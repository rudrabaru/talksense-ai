import asyncio
import time
import sys
import os
import numpy as np

sys.path.append(os.path.join(os.getcwd(), "backend"))

from audio.transcriber import get_transcriber
from audio.diarizer import get_diarizer
from audio.speaker_profile import SpeakerProfile

# Mock a 2.0s PCM chunk
sample_rate = 16000
duration = 2.0
samples = int(sample_rate * duration)
# sine wave 440hz
t = np.linspace(0, duration, samples, False)
audio_float = np.sin(440 * 2 * np.pi * t)
audio_int16 = (audio_float * 32767).astype(np.int16)
pcm_bytes = audio_int16.tobytes()


async def simulate_session(session_id: int):
    t_start = time.perf_counter()
    transcriber = get_transcriber()
    diarizer = get_diarizer()
    profile = SpeakerProfile()

    # 1. Transcribe
    t0 = time.perf_counter()
    segments = await transcriber.transcribe_async(pcm_bytes)
    t_transcribe = time.perf_counter() - t0

    # 2. Diarize
    t1 = time.perf_counter()
    _ = await diarizer.assign_speakers_async(
        segments,
        pcm_bytes,
        chunk_time_offset=0.0,
        fallback_speaker="Speaker 1",
        speaker_profile=profile,
    )
    t_diarize = time.perf_counter() - t1

    total = time.perf_counter() - t_start
    print(
        f"Session {session_id} finished in {total * 1000:.1f}ms (Whisper: {t_transcribe * 1000:.1f}ms, Pyannote: {t_diarize * 1000:.1f}ms)"
    )
    return total


async def main():
    transcriber = get_transcriber()
    diarizer = get_diarizer()
    print("Loading models...")
    transcriber.load("small", "int8", "cuda")
    diarizer.load(os.environ.get("HF_TOKEN", ""), "cuda")

    print("\n--- Single Session Benchmark ---")
    await simulate_session(1)

    print("\n--- Dual Session Benchmark ---")
    t0 = time.perf_counter()
    await asyncio.gather(simulate_session(2), simulate_session(3))
    print(f"Dual session total time: {(time.perf_counter() - t0) * 1000:.1f}ms")


if __name__ == "__main__":
    asyncio.run(main())
