"""
TalkSense AI — Voice Activity Detection

Wraps Silero VAD to filter silence before sending audio to Whisper.

Audio contract (enforced upstream by AudioBuffer):
  - PCM 16kHz, mono, 16-bit signed integers
  - Chunks of 100–250ms (1600–4000 samples at 16kHz)

Silero VAD runs on CPU (it's tiny, ~1MB) to keep GPU free for Whisper.
"""

import logging
import threading

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Silero VAD recommended chunk sizes at 16kHz
# 512 = 32ms | 1024 = 64ms | 1536 = 96ms
_CHUNK_SIZES = {16000: 512}


class VADSessionProcessor:
    """
    Session-isolated Silero VAD wrapper for speech detection.

    Contains a deepcopy of the base model to isolate the recurrent LSTM hidden state.
    """

    def __init__(self, base_model, threshold: float = 0.60, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._chunk_size = _CHUNK_SIZES[sample_rate]

        import copy

        self._model = copy.deepcopy(base_model) if base_model is not None else None
        if self._model is not None:
            self._loaded = True
            self.reset()
        else:
            self._loaded = False

    def is_speech(self, pcm_bytes: bytes) -> bool:
        """
        Returns True if the audio chunk contains speech.
        """
        if not self._loaded or self._model is None:
            return True  # pass-through fallback

        try:
            # Convert bytes → float32 tensor in [-1, 1]
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            # Evaluate sliding windows of chunk_size
            num_windows = max(1, len(audio_float32) // self._chunk_size)

            for i in range(num_windows):
                start = i * self._chunk_size
                window = audio_float32[start : start + self._chunk_size]

                if len(window) < self._chunk_size:
                    window = np.pad(window, (0, self._chunk_size - len(window)))

                audio_tensor = torch.from_numpy(window)
                with torch.no_grad():
                    speech_prob = self._model(audio_tensor, self.sample_rate).item()

                if speech_prob >= self.threshold:
                    return True

            return False

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


class VADFactory:
    """
    Global factory that loads the PyTorch model once, then spawns isolated
    session processors using deepcopy.
    """

    def __init__(self):
        self._base_model = None

    def load(self) -> None:
        """Load Silero VAD model (CPU, called once at startup)."""
        try:
            from typing import Any

            trust_repo_val: Any = True
            res: Any = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                trust_repo=trust_repo_val,
            )
            self._base_model, _ = res
            self._base_model.eval()
            logger.info("VAD: Silero VAD loaded on CPU")
        except Exception as exc:
            logger.error(
                f"VAD: Failed to load Silero VAD — {exc}. Falling back to pass-through mode."
            )
            self._base_model = None

    def create_session_vad(self) -> VADSessionProcessor:
        """Returns an isolated VAD session wrapper with its own LSTM state."""
        return VADSessionProcessor(base_model=self._base_model)


# ── Module-level singleton (shared across all sessions) ───────────────────────
_vad_factory: VADFactory | None = None


def get_vad() -> VADFactory:
    """Return the module-level VAD factory singleton."""
    global _vad_factory
    if _vad_factory is None:
        _vad_factory = VADFactory()
        _vad_factory.load()
    return _vad_factory
