"""
TalkSense AI — Audio Accumulation Buffer

Accumulates VAD-approved PCM chunks from the WebSocket stream and
flushes to Whisper when enough speech audio has been collected.

Flush strategy:
  - Flush when buffer reaches TARGET_DURATION_MS of speech audio.
  - Force-flush on silence gap (SILENCE_GAP_MS) after speech burst.
  - Always flush on session end regardless of buffer size.

Audio contract:
  PCM, 16kHz, mono, 16-bit signed integer (2 bytes per sample)
"""
import logging
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000          # Hz
BYTES_PER_SAMPLE = 2          # int16
SAMPLES_PER_MS = SAMPLE_RATE // 1000  # 16 samples per ms

TARGET_DURATION_MS = 1_000    # Flush after 1s of speech audio
SILENCE_GAP_MS = 800          # Flush after 800ms of silence following speech
MIN_FLUSH_MS = 300            # Don't flush tiny chunks < 300ms


@dataclass
class AudioBuffer:
    """
    Per-session audio accumulation buffer.

    Each WebSocket session gets its own AudioBuffer instance.
    Not thread-safe — caller must ensure single-writer access.
    """

    _chunks: deque = field(default_factory=deque)
    _buffered_ms: float = 0.0
    _last_speech_time: float = field(default_factory=time.monotonic)
    _speech_active: bool = False

    def __post_init__(self):
        self._last_speech_time = time.monotonic()

    # ── Public interface ──────────────────────────────────────────────────────

    def push(self, pcm_bytes: bytes, is_speech: bool) -> bytes | None:
        """
        Push a PCM chunk into the buffer.

        Args:
            pcm_bytes:  Raw PCM bytes conforming to the audio contract.
            is_speech:  Whether VAD classified this chunk as speech.

        Returns:
            Flushed PCM bytes if a flush condition is met, else None.
        """
        now = time.monotonic()
        chunk_ms = self._bytes_to_ms(pcm_bytes)

        if is_speech:
            self._chunks.append(pcm_bytes)
            self._buffered_ms += chunk_ms
            self._last_speech_time = now
            self._speech_active = True

            # Flush condition 1: target duration reached
            if self._buffered_ms >= TARGET_DURATION_MS:
                return self._flush()

        else:
            # Flush condition 2: silence gap after speech burst
            silence_gap_ms = (now - self._last_speech_time) * 1000
            if self._speech_active and silence_gap_ms >= SILENCE_GAP_MS:
                self._speech_active = False
                if self._buffered_ms >= MIN_FLUSH_MS:
                    return self._flush()

        return None

    def flush_remaining(self) -> bytes | None:
        """
        Force-flush whatever is left (called on session end).

        Returns:
            Remaining PCM bytes, or None if buffer is empty / too small.
        """
        if self._buffered_ms >= MIN_FLUSH_MS:
            return self._flush()
        self._clear()
        return None

    @property
    def buffered_ms(self) -> float:
        """Current buffered audio duration in milliseconds."""
        return self._buffered_ms

    # ── Private helpers ───────────────────────────────────────────────────────

    def _flush(self) -> bytes:
        """Concatenate all chunks, clear buffer, return bytes."""
        audio = b"".join(self._chunks)
        self._clear()
        logger.debug(f"AudioBuffer: flushed {len(audio)} bytes")
        return audio

    def _clear(self) -> None:
        self._chunks.clear()
        self._buffered_ms = 0.0

    @staticmethod
    def _bytes_to_ms(pcm_bytes: bytes) -> float:
        """Convert byte count to milliseconds of 16kHz mono 16-bit audio."""
        num_samples = len(pcm_bytes) / BYTES_PER_SAMPLE
        return (num_samples / SAMPLE_RATE) * 1000
