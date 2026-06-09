"""
TalkSense AI — Speaker Diarization (Pyannote)

Assigns speaker labels to TranscriptSegments by running Pyannote's
speaker diarization pipeline on the same audio chunk.

VRAM Strategy (RTX 3050, 4GB):
  - Whisper and Pyannote share the GPU but run SEQUENTIALLY per chunk.
  - Whisper transcribes first → releases GPU memory → Pyannote diarizes.
  - This keeps peak VRAM under ~2.5GB.

Fallback:
  If Pyannote is disabled (PYANNOTE_ENABLED=false) or fails to load,
  speakers are assigned via a simple turn-boundary heuristic: speaker
  alternates when > 1.5s of silence is detected between segments.
"""
import logging
import time
import numpy as np
from dataclasses import dataclass

from audio.transcriber import TranscriptSegment

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
SILENCE_TURN_THRESHOLD = 1.5   # seconds; gap > this → likely speaker change


@dataclass
class DiarizedSegment(TranscriptSegment):
    """TranscriptSegment extended with a confirmed speaker label."""
    speaker: str = "Speaker 1"  # type: ignore


class SpeakerDiarizer:
    """
    Pyannote-based speaker diarizer with heuristic fallback.

    Usage:
        diarizer = SpeakerDiarizer()
        diarizer.load(hf_token="hf_...", device="cuda")
        segments = diarizer.assign_speakers(transcript_segments, pcm_bytes)
    """

    def __init__(self):
        self._pipeline = None
        self._loaded = False

    def load(self, hf_token: str, device: str) -> None:
        """
        Load Pyannote pipeline.  Called once at app startup.
        Skipped if hf_token is empty or PYANNOTE_ENABLED=false.
        """
        if not hf_token:
            logger.info("Diarizer: No HF_TOKEN provided — using heuristic fallback.")
            return

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*torchcodec is not installed correctly.*",
                    category=UserWarning,
                )
                from pyannote.audio import Pipeline
            import torch

            logger.info(f"Diarizer: Loading pyannote/speaker-diarization-3.1 on {device} …")
            t0 = time.monotonic()

            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token,
            )
            self._pipeline.to(torch.device(device))

            elapsed = time.monotonic() - t0
            logger.info(f"Diarizer: Ready in {elapsed:.1f}s")
            self._loaded = True

        except Exception as exc:
            logger.error(f"Diarizer: Failed to load — {exc}. Using heuristic fallback.")
            self._loaded = False

    def assign_speakers(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float = 0.0,
        fallback_speaker: str = "Speaker 1",
    ) -> list[DiarizedSegment]:
        """
        Assign speaker labels to transcript segments.

        Tries Pyannote first; falls back to heuristic if unavailable.

        Args:
            segments:          Output of WhisperTranscriber.transcribe().
            pcm_bytes:         The same raw PCM chunk used for transcription.
            chunk_time_offset: Absolute time of the chunk start (seconds).
            fallback_speaker:  Speaker to assign if chunk is too short.

        Returns:
            List of DiarizedSegment with speaker labels.
        """
        if not segments:
            return []

        if self._loaded and self._pipeline is not None:
            return self._diarize_with_pyannote(segments, pcm_bytes, chunk_time_offset, fallback_speaker)
        else:
            return self._diarize_heuristic(segments, fallback_speaker)

    # ── Pyannote diarization ──────────────────────────────────────────────────

    def _diarize_with_pyannote(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float,
        fallback_speaker: str,
    ) -> list[DiarizedSegment]:
        """Run Pyannote on the audio and map turns to Whisper segments."""
        try:
            import torch
            from pyannote.core import Segment as PyannoteSegment

            # Convert PCM → float32 tensor
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            
            # Guard: Pyannote clustering fails on extremely short chunks (e.g. < 0.5s)
            # leading to divide-by-zero errors. Minimum recommended is ~1.5s.
            duration = len(audio_int16) / SAMPLE_RATE
            if duration < 1.5:
                logger.warning(f"Diarizer: Chunk too short ({duration:.2f}s < 1.5s). Falling back to previous speaker.")
                return self._diarize_heuristic(segments, fallback_speaker)

            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)  # [1, samples]

            waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

            t0 = time.monotonic()
            diarization = self._pipeline(waveform)
            elapsed = (time.monotonic() - t0) * 1000
            logger.debug(f"Diarizer: Pyannote finished in {elapsed:.0f}ms")

            # pyannote-audio 4.x returns a DiarizeOutput dataclass, not an
            # Annotation directly.  Unwrap it to get the pyannote.core.Annotation
            # that actually carries the itertracks() API.
            from pyannote.audio.pipelines.speaker_diarization import DiarizeOutput
            if isinstance(diarization, DiarizeOutput):
                annotation = diarization.speaker_diarization
            else:
                # Legacy mode / future-proofing: if already an Annotation, use as-is
                annotation = diarization

            # Build a list of (start, end, speaker) turns from Pyannote output
            turns: list[tuple[float, float, str]] = []
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                # Adjust times to absolute session time
                turns.append((
                    turn.start + chunk_time_offset,
                    turn.end + chunk_time_offset,
                    speaker,
                ))

            # Assign speaker to each Whisper segment by overlap
            diarized: list[DiarizedSegment] = []
            for seg in segments:
                speaker = self._find_speaker(seg.start, seg.end, turns)
                diarized.append(DiarizedSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    speaker=speaker,
                    language=seg.language,
                    avg_logprob=seg.avg_logprob,
                ))

            return diarized

        except Exception as exc:
            logger.error(f"Diarizer: Pyannote inference error — {exc}. Falling back.")
            return self._diarize_heuristic(segments, fallback_speaker)

    @staticmethod
    def _find_speaker(
        seg_start: float,
        seg_end: float,
        turns: list[tuple[float, float, str]],
    ) -> str:
        """Return the speaker with the most overlap with the given segment."""
        best_speaker = "Speaker 1"
        best_overlap = 0.0

        for turn_start, turn_end, speaker in turns:
            overlap = min(seg_end, turn_end) - max(seg_start, turn_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker

        return best_speaker

    # ── Heuristic fallback ────────────────────────────────────────────────────

    @staticmethod
    def _diarize_heuristic(
        segments: list[TranscriptSegment],
        fallback_speaker: str = "Speaker 1",
    ) -> list[DiarizedSegment]:
        """
        Assign speakers based on silence gaps between segments.

        Logic: If gap between previous segment end and current segment start
        exceeds SILENCE_TURN_THRESHOLD, toggle the speaker label.
        """
        current_speaker = fallback_speaker
        diarized: list[DiarizedSegment] = []
        prev_end = 0.0

        for seg in segments:
            gap = seg.start - prev_end
            if gap > SILENCE_TURN_THRESHOLD and diarized:
                # Switch speaker on long silence. We just flip the number if possible.
                if current_speaker == "Speaker 1":
                    current_speaker = "Speaker 2"
                elif current_speaker == "Speaker 2":
                    current_speaker = "Speaker 1"

            diarized.append(DiarizedSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                speaker=current_speaker,
                language=seg.language,
                avg_logprob=seg.avg_logprob,
            ))
            prev_end = seg.end

        return diarized


# ── Module-level singleton ────────────────────────────────────────────────────
_diarizer_instance: SpeakerDiarizer | None = None


def get_diarizer() -> SpeakerDiarizer:
    """Return the module-level Diarizer singleton."""
    global _diarizer_instance
    if _diarizer_instance is None:
        _diarizer_instance = SpeakerDiarizer()
    return _diarizer_instance
