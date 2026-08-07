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

Post-session diarization:
  Every speech PCM chunk is also appended to a session-scoped WAV file
  on disk.  This keeps memory usage constant (O(1)) regardless of meeting
  length, while giving the post-session diarizer a valid WAV file to read.
  The WAV file is created on first speech and closed on flush_remaining().
"""

import logging
import os
import struct
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000  # Hz
BYTES_PER_SAMPLE = 2  # int16
SAMPLES_PER_MS = SAMPLE_RATE // 1000  # 16 samples per ms

TARGET_DURATION_MS: int = (
    2_000  # Flush after 2.0s — Whisper accuracy peaks with longer chunks
)
SILENCE_GAP_MS: int = 600  # Flush faster after speaker stops (was 800ms)
MIN_FLUSH_MS: int = (
    800  # Reject chunks < 800ms — avoids Whisper hallucination on tiny fragments
)
OVERLAP_MS: int = 1_000  # Retain 1.0s of overlap on partial flushes

# Directory for session WAV files (relative to backend working directory)
SESSION_AUDIO_DIR = "session_audio"


def _ensure_audio_dir() -> str:
    """Create and return the absolute path to the session audio directory."""
    audio_dir = os.path.abspath(SESSION_AUDIO_DIR)
    os.makedirs(audio_dir, exist_ok=True)
    return audio_dir


def _wav_header(num_data_bytes: int) -> bytes:
    """
    Build a 44-byte RIFF WAV header for 16kHz mono 16-bit PCM.

    The data-chunk size is written here but the file is always readable
    because we call finalize_wav() at session end to rewrite the correct sizes.
    We pass 0 initially because we don't know the final size while streaming.
    """
    num_channels = 1
    bits_per_sample = 16
    byte_rate = SAMPLE_RATE * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + num_data_bytes,  # ChunkSize (file size - 8)
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size (PCM)
        1,  # AudioFormat (PCM = 1)
        num_channels,
        SAMPLE_RATE,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        num_data_bytes,  # Subchunk2Size
    )
    return header


@dataclass
class AudioBuffer:
    """
    Per-session audio accumulation buffer.

    Each WebSocket session gets its own AudioBuffer instance.
    Not thread-safe — caller must ensure single-writer access.

    Disk WAV accumulation:
        All speech PCM is appended to a session-scoped WAV file in
        SESSION_AUDIO_DIR.  The live-flush pipeline (push / flush_remaining)
        is unchanged — only the _all_audio_file side-path is new.
    """

    _session_id: str = ""

    _chunks: deque = field(default_factory=deque)
    _buffered_ms: float = 0.0
    _silence_duration_ms: float = 0.0
    _speech_active: bool = False

    # ── WAV file accumulator (disk) ───────────────────────────────────────────
    _wav_path: str | None = None  # None until first speech chunk
    _wav_file = None  # raw file handle (binary append)
    _wav_data_bytes: int = 0  # running count of PCM bytes written

    _total_bytes_received: int = 0
    _chunk_start_bytes: int = 0
    _total_speech_chunks: int = 0
    _total_nonspeech_chunks: int = 0

    def __post_init__(self):
        pass

    # ── Public interface ──────────────────────────────────────────────────────

    def push(
        self, pcm_bytes: bytes, is_speech: bool
    ) -> tuple[bytes, float, bool] | None:
        """
        Push a PCM chunk into the buffer.

        Args:
            pcm_bytes:  Raw PCM bytes conforming to the audio contract.
            is_speech:  Whether VAD classified this chunk as speech.

        Returns:
            Tuple of (flushed_pcm_bytes, start_time_offset_seconds, is_partial)
            if flushed, else None.
        """
        # Always write ALL incoming audio to WAV to maintain correct timeline
        self._write_to_wav(pcm_bytes)

        chunk_ms = self._bytes_to_ms(pcm_bytes)
        result = None

        if is_speech:
            self._total_speech_chunks += 1
            self._silence_duration_ms = 0.0
            if not self._speech_active:
                self._speech_active = True
                self._chunk_start_bytes = self._total_bytes_received
        else:
            self._total_nonspeech_chunks += 1
            if self._speech_active:
                self._silence_duration_ms += chunk_ms

        if self._speech_active:
            self._chunks.append(pcm_bytes)
            self._buffered_ms += chunk_ms

            # Flush condition 1: target duration reached
            if self._buffered_ms >= TARGET_DURATION_MS:
                result = self._flush(is_partial=True)
            else:
                # Flush condition 2: silence gap after speech burst
                if self._silence_duration_ms >= SILENCE_GAP_MS:
                    self._speech_active = False
                    if self._buffered_ms >= MIN_FLUSH_MS:
                        result = self._flush(is_partial=False)
                    else:
                        self._clear()

        self._total_bytes_received += len(pcm_bytes)

        if result is not None:
            flushed, time_offset, is_partial = result
            return flushed, time_offset, is_partial

        return None

    def flush_remaining(self) -> tuple[bytes, float, bool] | None:
        """
        Force-flush whatever is left (called on session end).

        Also finalizes the WAV file by rewriting the RIFF/data chunk sizes.

        Returns:
            Tuple of (remaining_pcm_bytes, start_time_offset_seconds, is_partial),
            or None if buffer is empty / too small.
        """
        from utils.profiler import profile_stage

        with profile_stage(self._session_id, "Save WAV"):
            result = None
            if self._buffered_ms >= MIN_FLUSH_MS:
                result = self._flush(is_partial=False)
            else:
                self._clear()

            # Always finalize and close the WAV file on session end
            self._finalize_wav()

            if result is not None:
                flushed, time_offset, is_partial = result
                return flushed, time_offset, is_partial

            return None

    def get_audio_file_path(self) -> str | None:
        """
        Return the absolute path to the session WAV file, or None if no
        speech audio was received (empty session).
        """
        return self._wav_path

    @property
    def buffered_ms(self) -> float:
        """Current buffered audio duration in milliseconds."""
        return self._buffered_ms

    # ── Private helpers ───────────────────────────────────────────────────────

    def _flush(self, is_partial: bool = False) -> tuple[bytes, float, bool]:
        """Concatenate all chunks, manage overlap, return bytes and time offset."""
        audio = b"".join(self._chunks)
        start_time_offset = self._chunk_start_bytes / (SAMPLE_RATE * BYTES_PER_SAMPLE)

        if is_partial:
            overlap_bytes = int((OVERLAP_MS / 1000) * SAMPLE_RATE * BYTES_PER_SAMPLE)
            total_bytes = len(audio)
            drop_bytes = max(0, total_bytes - overlap_bytes)

            self._chunk_start_bytes += drop_bytes
            self._chunks.clear()

            overlap_audio = (
                audio[-overlap_bytes:] if overlap_bytes < total_bytes else audio
            )
            self._chunks.append(overlap_audio)
            self._buffered_ms = self._bytes_to_ms(overlap_audio)
        else:
            self._clear()

        logger.debug(
            "AudioBuffer: flushed %d bytes at offset %.2fs (partial=%s)",
            len(audio),
            start_time_offset,
            is_partial,
        )
        return audio, start_time_offset, is_partial

    def _clear(self) -> None:
        self._chunks.clear()
        self._buffered_ms = 0.0
        self._speech_active = False

    @staticmethod
    def _bytes_to_ms(pcm_bytes: bytes) -> float:
        """Convert byte count to milliseconds of 16kHz mono 16-bit audio."""
        num_samples = len(pcm_bytes) / BYTES_PER_SAMPLE
        return (num_samples / SAMPLE_RATE) * 1000

    # ── WAV file I/O ──────────────────────────────────────────────────────────

    def _write_to_wav(self, pcm_bytes: bytes) -> None:
        """
        Append raw PCM bytes to the session WAV file.

        Opens the file on first call (writes placeholder header).
        Subsequent calls append raw PCM data after the header.
        """
        try:
            if self._wav_file is None:
                audio_dir = _ensure_audio_dir()
                session_id = self._session_id if self._session_id else "unknown"
                filename = f"session_{session_id}.wav"
                self._wav_path = os.path.join(audio_dir, filename)

                # Open in write+binary mode; write placeholder header (0 bytes data)
                self._wav_file = open(self._wav_path, "wb")
                self._wav_file.write(_wav_header(0))
                logger.debug("AudioBuffer: opened WAV file %s", self._wav_path)

            # Append raw PCM (no header) after initial header
            self._wav_file.write(pcm_bytes)
            self._wav_data_bytes += len(pcm_bytes)

        except OSError as exc:
            logger.error("AudioBuffer: failed to write to WAV file — %s", exc)

    def _finalize_wav(self) -> None:
        """
        Rewrite the RIFF and data chunk sizes in the WAV header so the file
        is valid for any consumer (Pyannote, ffprobe, etc.).

        Called once from flush_remaining() when the session ends.
        """
        if self._wav_file is None:
            return  # no speech was received — nothing to finalize

        try:
            self._wav_file.close()

            if self._wav_path and os.path.exists(self._wav_path):
                # Rewrite correct sizes at the known fixed offsets:
                #   offset 4  → ChunkSize  = 36 + data_bytes
                #   offset 40 → data chunk = data_bytes
                with open(self._wav_path, "r+b") as f:
                    f.seek(4)
                    f.write(struct.pack("<I", 36 + self._wav_data_bytes))
                    f.seek(40)
                    f.write(struct.pack("<I", self._wav_data_bytes))

                logger.info(
                    "audio stats: received=%d written=%d speech=%d nonspeech=%d "
                    "duration=%.2fs",
                    self._total_bytes_received,
                    self._wav_data_bytes,
                    self._total_speech_chunks,
                    self._total_nonspeech_chunks,
                    self._wav_data_bytes / (SAMPLE_RATE * BYTES_PER_SAMPLE),
                )

        except OSError as exc:
            logger.error("AudioBuffer: failed to finalise WAV file — %s", exc)
        finally:
            self._wav_file = None
