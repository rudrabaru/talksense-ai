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

from audio.speaker_profile import SpeakerProfile
from audio.transcriber import TranscriptSegment

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

            model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM",
                token=hf_token,
            )
            if model is None:
                raise ValueError(
                    "Model.from_pretrained returned None. Check HF token/network."
                )
            self._model = model
            self._model.to(torch.device(device))
            self._model.eval()

            logger.info("Diarizer: Running warm-up inference ...")
            # Run a dummy 2.0s tensor to initialize CUDA kernels and PyTorch caches
            dummy_waveform = torch.zeros(1, 1, SAMPLE_RATE * 2, dtype=torch.float32).to(
                torch.device(device)
            )
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
                segments,
                pcm_bytes,
                chunk_time_offset,
                fallback_speaker,
                speaker_profile,
            )
        else:
            return self._diarize_heuristic(segments, fallback_speaker)

    async def assign_speakers_async(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float = 0.0,
        fallback_speaker: str = "Speaker 1",
        speaker_profile: SpeakerProfile | None = None,
    ) -> list[DiarizedSegment]:
        """
        Async version of assign_speakers that separates CPU prep/post from
        serialized GPU inference via the global semaphore.
        """
        import asyncio

        loop = asyncio.get_running_loop()

        if not segments:
            return []

        if self._loaded and self._model is not None and speaker_profile is not None:
            return await self._diarize_with_embeddings_async(
                segments,
                pcm_bytes,
                chunk_time_offset,
                fallback_speaker,
                speaker_profile,
            )
        else:
            return await loop.run_in_executor(
                None, self._diarize_heuristic, segments, fallback_speaker
            )

    # ── Pyannote diarization ──────────────────────────────────────────────────

    def _diarize_with_embeddings(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float,
        fallback_speaker: str,
        speaker_profile: SpeakerProfile,
    ) -> list[DiarizedSegment]:
        """Extract sliding window embeddings and align via word overlap."""
        if self._model is None:
            raise ValueError("Diarizer model is not loaded.")
        try:
            import torch

            from audio.transcriber import TranscriptWord
            from services.word_speaker_aligner import align_words_to_speakers

            # Convert PCM → float32 tensor
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            device = next(self._model.parameters()).device

            speaker_segments = []
            window_samples = int(1.0 * SAMPLE_RATE)
            stride_samples = int(0.5 * SAMPLE_RATE)
            total_samples = len(audio_float32)

            # Sliding window to get Pyannote speaker segments
            if total_samples < window_samples and total_samples >= SAMPLE_RATE * 0.5:
                tensor = (
                    torch.from_numpy(audio_float32).unsqueeze(0).unsqueeze(0).to(device)
                )
                with torch.inference_mode():
                    emb = self._model(tensor).cpu().numpy()[0]
                speaker = speaker_profile.match_or_create(emb)
                speaker_segments.append(
                    (
                        chunk_time_offset,
                        chunk_time_offset + (total_samples / SAMPLE_RATE),
                        speaker,
                    )
                )
            elif total_samples >= window_samples:
                for start_sample in range(0, total_samples, stride_samples):
                    end_sample = min(total_samples, start_sample + window_samples)
                    seg_audio = audio_float32[start_sample:end_sample]
                    if len(seg_audio) >= SAMPLE_RATE * 0.5:
                        tensor = (
                            torch.from_numpy(seg_audio)
                            .unsqueeze(0)
                            .unsqueeze(0)
                            .to(device)
                        )
                        with torch.inference_mode():
                            emb = self._model(tensor).cpu().numpy()[0]
                        speaker = speaker_profile.match_or_create(emb)
                        w_start = chunk_time_offset + (start_sample / SAMPLE_RATE)
                        w_end = chunk_time_offset + (end_sample / SAMPLE_RATE)
                        speaker_segments.append((w_start, w_end, speaker))

            diarized: list[DiarizedSegment] = []

            for seg in segments:
                words_dicts = []
                if seg.words:
                    for w in seg.words:
                        words_dicts.append(
                            {
                                "word": w.word,
                                "start": w.start,
                                "end": w.end,
                                "probability": w.probability,
                            }
                        )
                else:
                    words_dicts.append(
                        {
                            "word": seg.text,
                            "start": seg.start,
                            "end": seg.end,
                            "probability": seg.avg_logprob,
                        }
                    )

                aligned = align_words_to_speakers(
                    words_dicts, speaker_segments, fallback_speaker
                )

                if not aligned:
                    continue

                current_seg_speaker = aligned[0]["speaker"]
                current_seg_words = []

                for w in aligned:
                    if w["speaker"] != current_seg_speaker:
                        if current_seg_words:
                            text = "".join(x["word"] for x in current_seg_words).strip()
                            t_words = [
                                TranscriptWord(
                                    word=x["word"],
                                    start=x["start"],
                                    end=x["end"],
                                    probability=x["confidence"],
                                )
                                for x in current_seg_words
                            ]
                            diarized.append(
                                DiarizedSegment(
                                    start=current_seg_words[0]["start"],
                                    end=current_seg_words[-1]["end"],
                                    text=text,
                                    speaker=current_seg_speaker,
                                    language=seg.language,
                                    avg_logprob=seg.avg_logprob,
                                    words=t_words,
                                )
                            )
                        current_seg_speaker = w["speaker"]
                        current_seg_words = [w]
                    else:
                        current_seg_words.append(w)

                if current_seg_words:
                    text = "".join(x["word"] for x in current_seg_words).strip()
                    t_words = [
                        TranscriptWord(
                            word=x["word"],
                            start=x["start"],
                            end=x["end"],
                            probability=x["confidence"],
                        )
                        for x in current_seg_words
                    ]
                    diarized.append(
                        DiarizedSegment(
                            start=current_seg_words[0]["start"],
                            end=current_seg_words[-1]["end"],
                            text=text,
                            speaker=current_seg_speaker,
                            language=seg.language,
                            avg_logprob=seg.avg_logprob,
                            words=t_words,
                        )
                    )

            return diarized

        except Exception as exc:
            logger.error(
                f"Diarizer: Embedding inference error — {exc}. Falling back.",
                exc_info=True,
            )
            return self._diarize_heuristic(segments, fallback_speaker)

    async def _diarize_with_embeddings_async(
        self,
        segments: list[TranscriptSegment],
        pcm_bytes: bytes,
        chunk_time_offset: float,
        fallback_speaker: str,
        speaker_profile: SpeakerProfile,
    ) -> list[DiarizedSegment]:
        """Async embedding extraction with serialized GPU access."""
        if self._model is None:
            raise ValueError("Diarizer model is not loaded.")
        import asyncio

        import torch

        from audio.gpu_manager import get_gpu_semaphore
        from audio.transcriber import TranscriptWord
        from services.word_speaker_aligner import align_words_to_speakers

        loop = asyncio.get_running_loop()
        device = next(self._model.parameters()).device

        # 1. CPU Prep
        def _prep():
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            tensors = []
            window_samples = int(1.0 * SAMPLE_RATE)
            stride_samples = int(0.5 * SAMPLE_RATE)
            total_samples = len(audio_float32)

            if total_samples < window_samples and total_samples >= SAMPLE_RATE * 0.5:
                tensors.append(
                    torch.from_numpy(audio_float32).unsqueeze(0).unsqueeze(0).to(device)
                )
            elif total_samples >= window_samples:
                for start_sample in range(0, total_samples, stride_samples):
                    end_sample = min(total_samples, start_sample + window_samples)
                    seg_audio = audio_float32[start_sample:end_sample]
                    if len(seg_audio) >= SAMPLE_RATE * 0.5:
                        tensors.append(
                            torch.from_numpy(seg_audio)
                            .unsqueeze(0)
                            .unsqueeze(0)
                            .to(device)
                        )
            return tensors

        try:
            tensors = await loop.run_in_executor(None, _prep)

            # 2. GPU Inference
            embs = []
            if tensors:

                def _infer():
                    out = []
                    with torch.inference_mode():
                        for tensor in tensors:
                            out.append(self._model(tensor).cpu().numpy()[0])
                    return out

                async with get_gpu_semaphore():
                    embs = await loop.run_in_executor(None, _infer)

            # 3. CPU Post
            def _post():
                speaker_segments = []
                window_samples = int(1.0 * SAMPLE_RATE)
                stride_samples = int(0.5 * SAMPLE_RATE)
                total_samples = len(np.frombuffer(pcm_bytes, dtype=np.int16))

                if embs:
                    emb_idx = 0
                    if (
                        total_samples < window_samples
                        and total_samples >= SAMPLE_RATE * 0.5
                    ):
                        speaker = speaker_profile.match_or_create(embs[emb_idx])
                        speaker_segments.append(
                            (
                                chunk_time_offset,
                                chunk_time_offset + (total_samples / SAMPLE_RATE),
                                speaker,
                            )
                        )
                    elif total_samples >= window_samples:
                        for start_sample in range(0, total_samples, stride_samples):
                            end_sample = min(
                                total_samples, start_sample + window_samples
                            )
                            if end_sample - start_sample >= SAMPLE_RATE * 0.5:
                                speaker = speaker_profile.match_or_create(embs[emb_idx])
                                w_start = chunk_time_offset + (
                                    start_sample / SAMPLE_RATE
                                )
                                w_end = chunk_time_offset + (end_sample / SAMPLE_RATE)
                                speaker_segments.append((w_start, w_end, speaker))
                                emb_idx += 1

                diarized = []
                for seg in segments:
                    words_dicts = []
                    if seg.words:
                        for w in seg.words:
                            words_dicts.append(
                                {
                                    "word": w.word,
                                    "start": w.start,
                                    "end": w.end,
                                    "probability": w.probability,
                                }
                            )
                    else:
                        words_dicts.append(
                            {
                                "word": seg.text,
                                "start": seg.start,
                                "end": seg.end,
                                "probability": seg.avg_logprob,
                            }
                        )

                    aligned = align_words_to_speakers(
                        words_dicts, speaker_segments, fallback_speaker
                    )

                    if not aligned:
                        continue

                    current_seg_speaker = aligned[0]["speaker"]
                    current_seg_words = []

                    for w in aligned:
                        if w["speaker"] != current_seg_speaker:
                            if current_seg_words:
                                text = "".join(
                                    x["word"] for x in current_seg_words
                                ).strip()
                                t_words = [
                                    TranscriptWord(
                                        word=x["word"],
                                        start=x["start"],
                                        end=x["end"],
                                        probability=x["confidence"],
                                    )
                                    for x in current_seg_words
                                ]
                                diarized.append(
                                    DiarizedSegment(
                                        start=current_seg_words[0]["start"],
                                        end=current_seg_words[-1]["end"],
                                        text=text,
                                        speaker=current_seg_speaker,
                                        language=seg.language,
                                        avg_logprob=seg.avg_logprob,
                                        words=t_words,
                                    )
                                )
                            current_seg_speaker = w["speaker"]
                            current_seg_words = [w]
                        else:
                            current_seg_words.append(w)

                    if current_seg_words:
                        text = "".join(x["word"] for x in current_seg_words).strip()
                        t_words = [
                            TranscriptWord(
                                word=x["word"],
                                start=x["start"],
                                end=x["end"],
                                probability=x["confidence"],
                            )
                            for x in current_seg_words
                        ]
                        diarized.append(
                            DiarizedSegment(
                                start=current_seg_words[0]["start"],
                                end=current_seg_words[-1]["end"],
                                text=text,
                                speaker=current_seg_speaker,
                                language=seg.language,
                                avg_logprob=seg.avg_logprob,
                                words=t_words,
                            )
                        )

                return diarized

            return await loop.run_in_executor(None, _post)

        except Exception as exc:
            logger.error(
                f"Diarizer: Async embedding error — {exc}. Falling back.", exc_info=True
            )
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
