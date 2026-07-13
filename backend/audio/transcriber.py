"""
TalkSense AI — Faster Whisper Transcription Service

Wraps faster-whisper for real-time speech-to-text.

Model is loaded once at startup and shared across all sessions.
Transcription runs in a ThreadPoolExecutor to avoid blocking the
FastAPI event loop (Whisper releases the GIL during inference).

Config (from .env):
  WHISPER_MODEL        — tiny | base | small | medium | large-v3
  WHISPER_COMPUTE_TYPE — int8 | float16 | float32
  WHISPER_DEVICE       — cuda | cpu
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


@dataclass
class TranscriptWord:
    """A single transcribed word with timestamps."""

    word: str
    start: float
    end: float
    probability: float


@dataclass
class TranscriptSegment:
    """A single transcribed speech segment."""

    start: float  # seconds from session start
    end: float  # seconds from session start
    text: str
    speaker: str | None = None  # filled in by Diarizer later
    language: str | None = None
    avg_logprob: float = 0.0  # whisper confidence proxy
    words: list[TranscriptWord] | None = None


class WhisperTranscriber:
    """
    Faster Whisper singleton.

    Usage:
        transcriber = WhisperTranscriber()
        transcriber.load("small", "int8", "cuda")
        segments = transcriber.transcribe(pcm_bytes, time_offset=12.5)
    """

    def __init__(self):
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")
        self._loaded = False

    def load(self, model_name: str, compute_type: str, device: str) -> None:
        """
        Load the Whisper model.  Called once at app startup.

        Args:
            model_name:   "small", "medium", etc.
            compute_type: "int8" (GPU-efficient) or "float16".
            device:       "cuda" or "cpu".
        """
        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Whisper: Loading '{model_name}' on {device} ({compute_type}) …"
            )
            t0 = time.monotonic()
            self._model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                num_workers=2,  # overlaps CPU pre/post-processing with GPU inference
                download_root=None,  # uses HF cache
            )
            elapsed = time.monotonic() - t0
            logger.info(f"Whisper: Ready in {elapsed:.1f}s")
            self._loaded = True

        except Exception as exc:
            logger.error(f"Whisper: Failed to load — {exc}")
            self._loaded = False

    def transcribe(
        self,
        pcm_bytes: bytes,
        time_offset: float = 0.0,
        language: str | None = None,
        initial_prompt: str | None = None,
        is_partial: bool = False,
    ) -> list[TranscriptSegment]:
        """
        Transcribe a PCM chunk synchronously.

        Intended to be called from a ThreadPoolExecutor (not the async
        event loop directly) so the GIL release doesn't matter.

        Args:
            pcm_bytes:   Raw PCM, 16kHz mono 16-bit.
            time_offset: Session-relative time of the chunk start (seconds).
                         Added to segment timestamps so they are absolute.
            language:    Force a language (None = auto-detect).
            initial_prompt: Previous confirmed text to condition the decoder.

        Returns:
            List of TranscriptSegment.  Empty list on failure or silence.
        """
        if not self._loaded or self._model is None:
            logger.warning("Whisper: Model not loaded — skipping transcription.")
            return []

        if not pcm_bytes:
            return []

        try:
            # Convert PCM bytes → float32 numpy array in [-1.0, 1.0]
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            t0 = time.monotonic()
            raw_segments, info = self._model.transcribe(
                audio_float32,
                language=language,
                beam_size=3,  # was 5; ~35% faster, negligible accuracy loss
                best_of=1,  # disable sampling — deterministic greedy only
                patience=0.8,  # exit beam search early on confident outputs
                temperature=0.0,  # explicit deterministic; no sampling fallback
                no_speech_threshold=0.6,  # relaxed back to 0.6 to capture soft speech
                compression_ratio_threshold=2.2,  # was 2.4; reject repetitive hallucinations  # noqa: E501
                condition_on_previous_text=True,  # Use prior context across chunks
                initial_prompt=initial_prompt,  # Pass context manually
                vad_filter=True,  # Required for word_timestamps=True on long audio
                word_timestamps=True,
            )

            from audio.buffer import OVERLAP_MS
            chunk_duration_sec = len(pcm_bytes) / (SAMPLE_RATE * 2)
            tail_start = time_offset + chunk_duration_sec - (OVERLAP_MS / 1000.0)

            segments: list[TranscriptSegment] = []
            for seg in raw_segments:
                text = seg.text.strip()
                if not text:
                    continue
                
                # Reject punctuation-only segments (must have at least one alphanumeric char)
                if not re.search(r'[a-zA-Z0-9]', text):
                    continue

                segment_words = []
                if seg.words:
                    for w in seg.words:
                        w_start_abs = round(w.start + time_offset, 3)
                        w_end_abs = round(w.end + time_offset, 3)
                        
                        if is_partial and w_end_abs > tail_start:
                            continue  # Drop word in the overlapping tail
                            
                        segment_words.append(
                            TranscriptWord(
                                word=w.word,
                                start=w_start_abs,
                                end=w_end_abs,
                                probability=round(w.probability, 3),
                            )
                        )
                    
                    if not segment_words:
                        continue  # Entire segment was dropped
                    
                    # Reconstruct text from remaining words if any were dropped
                    if len(segment_words) != len(seg.words):
                        text = "".join(w.word for w in segment_words).strip()
                        if not text or not re.search(r'[a-zA-Z0-9]', text):
                            continue

                segments.append(
                    TranscriptSegment(
                        start=round(segment_words[0].start, 2) if segment_words else round(seg.start + time_offset, 2),
                        end=round(segment_words[-1].end, 2) if segment_words else round(seg.end + time_offset, 2),
                        text=text,
                        language=info.language,
                        avg_logprob=round(seg.avg_logprob, 3),
                        words=segment_words,
                    )
                )

            elapsed = (time.monotonic() - t0) * 1000
            logger.debug(
                f"Whisper: {len(segments)} segment(s) in {elapsed:.0f}ms "
                f"[lang={info.language}]"
            )
            return segments

        except Exception as exc:
            logger.error(f"Whisper: Transcription error — {exc}")
            return []

    async def transcribe_async(
        self,
        pcm_bytes: bytes,
        time_offset: float = 0.0,
        language: str | None = None,
        initial_prompt: str | None = None,
        is_partial: bool = False,
    ) -> list[TranscriptSegment]:
        """
        Async wrapper — runs transcription in the thread pool, separated into
        concurrent CPU prep/post and serialized GPU inference.
        """
        import asyncio

        from audio.gpu_manager import get_gpu_semaphore

        if not self._loaded or self._model is None or not pcm_bytes:
            return []

        loop = asyncio.get_running_loop()

        # 1. CPU Prep (concurrent)
        def _prep():
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            return audio_int16.astype(np.float32) / 32768.0

        audio_float32 = await loop.run_in_executor(self._executor, _prep)

        # 2. GPU Inference (serialized via semaphore)
        def _infer():
            assert self._model is not None, "Model is not loaded"
            t0 = time.monotonic()
            raw_segments, info = self._model.transcribe(
                audio_float32,
                language=language,
                beam_size=3,
                best_of=1,
                patience=0.8,
                temperature=0.0,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.2,
                condition_on_previous_text=True,
                initial_prompt=initial_prompt,
                vad_filter=True,
                word_timestamps=True,
            )
            # exhaust generator to execute inference immediately on GPU
            return list(raw_segments), info, time.monotonic() - t0

        async with get_gpu_semaphore():
            try:
                raw_segments, info, inference_time = await loop.run_in_executor(
                    self._executor, _infer
                )
            except Exception as exc:
                logger.error(f"Whisper: Transcription error — {exc}")
                return []

        # 3. CPU Postprocessing (concurrent)
        def _post():
            from audio.buffer import OVERLAP_MS
            chunk_duration_sec = len(pcm_bytes) / (SAMPLE_RATE * 2)
            tail_start = time_offset + chunk_duration_sec - (OVERLAP_MS / 1000.0)

            segments = []
            for seg in raw_segments:
                text = seg.text.strip()
                if not text:
                    continue
                
                # Reject punctuation-only segments
                if not re.search(r'[a-zA-Z0-9]', text):
                    continue

                segment_words = []
                if seg.words:
                    for w in seg.words:
                        w_start_abs = round(w.start + time_offset, 3)
                        w_end_abs = round(w.end + time_offset, 3)
                        
                        if is_partial and w_end_abs > tail_start:
                            continue
                            
                        segment_words.append(
                            TranscriptWord(
                                word=w.word,
                                start=w_start_abs,
                                end=w_end_abs,
                                probability=round(w.probability, 3),
                            )
                        )
                    
                    if not segment_words:
                        continue
                    
                    if len(segment_words) != len(seg.words):
                        text = "".join(w.word for w in segment_words).strip()
                        if not text or not re.search(r'[a-zA-Z0-9]', text):
                            continue

                segments.append(
                    TranscriptSegment(
                        start=round(segment_words[0].start, 2) if segment_words else round(seg.start + time_offset, 2),
                        end=round(segment_words[-1].end, 2) if segment_words else round(seg.end + time_offset, 2),
                        text=text,
                        language=info.language,
                        avg_logprob=round(seg.avg_logprob, 3),
                        words=segment_words,
                    )
                )

            return segments, inference_time, info.language

        segments, inference_time, lang = await loop.run_in_executor(
            self._executor, _post
        )

        elapsed_ms = inference_time * 1000
        logger.debug(
            f"Whisper: {len(segments)} segment(s) in {elapsed_ms:.0f}ms [lang={lang}]"
        )
        return segments


# ── Module-level singleton ────────────────────────────────────────────────────
_transcriber_instance: WhisperTranscriber | None = None


def get_transcriber() -> WhisperTranscriber:
    """Return the module-level Whisper singleton."""
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = WhisperTranscriber()
    return _transcriber_instance
