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
import io
import logging
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


@dataclass
class TranscriptSegment:
    """A single transcribed speech segment."""
    start: float          # seconds from session start
    end: float            # seconds from session start
    text: str
    speaker: str | None = None   # filled in by Diarizer later
    language: str | None = None
    avg_logprob: float = 0.0     # whisper confidence proxy


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
                download_root=None,   # uses HF cache
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
                beam_size=5,
                vad_filter=False,       # We handle VAD externally
                word_timestamps=False,  # Reduces latency
            )

            segments: list[TranscriptSegment] = []
            for seg in raw_segments:
                text = seg.text.strip()
                if not text:
                    continue
                segments.append(
                    TranscriptSegment(
                        start=round(seg.start + time_offset, 2),
                        end=round(seg.end + time_offset, 2),
                        text=text,
                        language=info.language,
                        avg_logprob=round(seg.avg_logprob, 3),
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
    ) -> list[TranscriptSegment]:
        """
        Async wrapper — runs transcription in the thread pool.
        Use this from async WebSocket handlers.
        """
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.transcribe(pcm_bytes, time_offset, language),
        )


# ── Module-level singleton ────────────────────────────────────────────────────
_transcriber_instance: WhisperTranscriber | None = None


def get_transcriber() -> WhisperTranscriber:
    """Return the module-level Whisper singleton."""
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = WhisperTranscriber()
    return _transcriber_instance
