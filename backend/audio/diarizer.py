"""
TalkSense AI — Speaker Diarization (Streaming Embeddings)

Extracts Speaker Embeddings from each Whisper segment and compares
against a persistent Session Speaker Profile to prevent cross-chunk amnesia.

VRAM Strategy:
  - Uses pyannote/wespeaker-voxceleb-resnet34-LM (small model).
  - Whisper and Embedding model run sequentially per chunk.

Fallback:
  If Pyannote is disabled or fails to load, speakers are assigned via a 
  simple heuristic.
"""

import logging
import time
from dataclasses import dataclass

import numpy as np

from audio.transcriber import TranscriptSegment
from audio.speaker_profile import SpeakerProfile

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
SILENCE_TURN_THRESHOLD = 1.5  # seconds; gap > this → likely speaker change


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
        from typing import Any

        self._model: Any = None
        self._loaded = False

    def load(self, hf_token: str, device: str) -> None:
        """
        Load Pyannote pipeline.  Called once at app startup.
        Skipped if hf_token is empty or PYANNOTE_ENABLED=false.
        """
        if not hf_token:
            logger.info("Diarizer: No HF_TOKEN provided — using heuristic fallback.")
            return

        import os

        os.environ["HF_TOKEN"] = hf_token

        try:
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*torchcodec is not installed correctly.*",
                    category=UserWarning,
                )
                from pyannote.audio import Model
            import torch

            logger.info(
                f"Diarizer: Loading pyannote/wespeaker-voxceleb-resnet34-LM on {device} …"
            )
            t0 = time.monotonic()

            self._model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM",
                use_auth_token=hf_token,
            )
            self._model.to(torch.device(device))
            self._model.eval()

            logger.info("Diarizer: Running warm-up inference ...")
            # Run a dummy 2.0s tensor to initialize CUDA kernels and PyTorch caches
            dummy_waveform = torch.zeros(1, 1, SAMPLE_RATE * 2, dtype=torch.float32).to(torch.device(device))
            with torch.inference_mode():
                _ = self._model(dummy_waveform)

            elapsed = time.monotonic() - t0
            logger.info(f"Diarizer: Ready and warmed up in {elapsed:.1f}s")
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
        speaker_profile: SpeakerProfile | None = None,
    ) -> list[DiarizedSegment]:
        """
        Assign speaker labels to transcript segments using Embeddings.

        Args:
            segments:          Output of WhisperTranscriber.transcribe().
            pcm_bytes:         The raw PCM chunk (15s rolling window or flushed).
            chunk_time_offset: Absolute time of the chunk start (seconds).
            fallback_speaker:  Speaker to assign if chunk is too short.
            speaker_profile:   Persistent session speaker profile.

        Returns:
            List of DiarizedSegment with speaker labels.
        """
        if not segments:
            return []

        if self._loaded and self._model is not None and speaker_profile is not None:
            return self._diarize_with_embeddings(
                segments, pcm_bytes, chunk_time_offset, fallback_speaker, speaker_profile
            )
        else:
            return self._diarize_heuristic(segments, fallback_speaker)

    # ── Pyannote diarization ──────────────────────────────────────────────────

    def _diarize_with_embeddings(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float,
        fallback_speaker: str,
        speaker_profile: SpeakerProfile,
    ) -> list[DiarizedSegment]:
        """Extract embeddings for each segment and assign via SpeakerProfile."""
        try:
            import torch

            # Convert PCM → float32 tensor
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            diarized: list[DiarizedSegment] = []
            current_speaker = fallback_speaker
            device = next(self._model.parameters()).device

            for seg in segments:
                # Calculate sample indices relative to the provided pcm chunk
                local_start = max(0.0, seg.start - chunk_time_offset)
                local_end = max(0.0, seg.end - chunk_time_offset)
                
                start_sample = int(local_start * SAMPLE_RATE)
                end_sample = int(local_end * SAMPLE_RATE)
                
                # Bounds check
                end_sample = min(len(audio_float32), end_sample)
                start_sample = min(end_sample, start_sample)
                
                seg_audio = audio_float32[start_sample:end_sample]
                
                # If segment is too short (< 0.5s), embedding will be noisy.
                # Just use the previous speaker (or fallback).
                if len(seg_audio) < SAMPLE_RATE * 0.5:
                    speaker = current_speaker
                else:
                    tensor = torch.from_numpy(seg_audio).unsqueeze(0).unsqueeze(0)  # [1, 1, samples]
                    tensor = tensor.to(device)
                    
                    with torch.inference_mode():
                        emb = self._model(tensor).cpu().numpy()[0]
                    
                    speaker = speaker_profile.match_or_create(emb)
                    current_speaker = speaker

                diarized.append(
                    DiarizedSegment(
                        start=seg.start,
                        end=seg.end,
                        text=seg.text,
                        speaker=speaker,
                        language=seg.language,
                        avg_logprob=seg.avg_logprob,
                    )
                )

            return diarized

        except Exception as exc:
            logger.error(f"Diarizer: Embedding inference error — {exc}. Falling back.")
            return self._diarize_heuristic(segments, fallback_speaker)

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

            diarized.append(
                DiarizedSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    speaker=current_speaker,
                    language=seg.language,
                    avg_logprob=seg.avg_logprob,
                )
            )
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
