"""
TalkSense AI — Voice Activity Detection

Wraps Silero VAD to filter silence before sending audio to Whisper.

Audio contract (enforced upstream by AudioBuffer):
  - PCM 16kHz, mono, 16-bit signed integers
  - Chunks of 100–250ms (1600–4000 samples at 16kHz)

Silero VAD runs on CPU (it's tiny, ~1MB) to keep GPU free for Whisper.
"""
import logging
import numpy as np
import torch

logger = logging.getLogger(__name__)

# Silero VAD recommended chunk sizes at 16kHz
# 512 = 32ms | 1024 = 64ms | 1536 = 96ms
_CHUNK_SIZES = {16000: 512}


class VADProcessor:
    """
    Silero VAD wrapper for speech detection.

    Usage:
        vad = VADProcessor()
        if vad.is_speech(pcm_bytes):
            # send to Whisper
    """

    def __init__(self, threshold: float = 0.60, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._chunk_size = _CHUNK_SIZES[sample_rate]
        self._model = None
        self._loaded = False

    def load(self) -> None:
        """Load Silero VAD model (CPU, called once at startup)."""
        try:
            self._model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                trust_repo=True,
            )
            self._model.eval()
            logger.info("VAD: Silero VAD loaded on CPU")
            self._loaded = True
        except Exception as exc:
            logger.error(f"VAD: Failed to load Silero VAD — {exc}. Falling back to pass-through mode.")
            self._loaded = False

    def is_speech(self, pcm_bytes: bytes) -> bool:
        """
        Returns True if the audio chunk contains speech.

        Falls back to True (pass-through) if VAD failed to load —
        this ensures transcription still works, just less efficient.

        Args:
            pcm_bytes: Raw PCM bytes, 16kHz mono 16-bit.

        Returns:
            bool: True if speech detected (or VAD unavailable).
        """
        if not self._loaded or self._model is None:
            return True  # pass-through fallback

        try:
            # Convert bytes → float32 tensor in [-1, 1]
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            # Silero needs exactly chunk_size samples; pad or truncate
            if len(audio_float32) < self._chunk_size:
                audio_float32 = np.pad(
                    audio_float32, (0, self._chunk_size - len(audio_float32))
                )
            audio_float32 = audio_float32[: self._chunk_size]

            audio_tensor = torch.from_numpy(audio_float32)

            with torch.no_grad():
                speech_prob = self._model(audio_tensor, self.sample_rate).item()

            return speech_prob >= self.threshold

        except Exception as exc:
            logger.warning(f"VAD: inference error — {exc}. Passing chunk through.")
            return True

    def reset(self) -> None:
        """Reset VAD state between sessions."""
        if self._loaded and self._model is not None:
            try:
                self._model.reset_states()
            except Exception:
                pass  # Some versions don't need explicit reset


# ── Module-level singleton (shared across all sessions) ───────────────────────
_vad_instance: VADProcessor | None = None


def get_vad() -> VADProcessor:
    """Return the module-level VAD singleton."""
    global _vad_instance
    if _vad_instance is None:
        _vad_instance = VADProcessor()
        _vad_instance.load()
    return _vad_instance
