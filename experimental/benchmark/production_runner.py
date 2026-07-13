import os
import sys
import json
import time
import asyncio
from pathlib import Path

# Add project root and backend to path so we can import backend
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from experimental.benchmark.common_schema import Segment, create_neutral_output
from backend.audio.diarizer import SpeakerDiarizer
from backend.audio.transcriber import WhisperTranscriber

async def run_production(wav_path: str, hf_token: str) -> dict:
    import psutil
    process = psutil.Process()
    
    t0 = time.time()
    
    # Initialize production models
    diarizer = SpeakerDiarizer()
    diarizer.load(hf_token, device="cpu")
    transcriber = WhisperTranscriber()
    transcriber.load(model_name="tiny", compute_type="int8", device="cpu")
    
    load_time = time.time() - t0
    
    t_inf = time.time()
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
        
    transcript_segments = transcriber.transcribe(audio_bytes, language="en")
    
    from backend.audio.speaker_profile import SpeakerProfile
    speaker_profile = SpeakerProfile()
    
    transcript_segments = diarizer.assign_speakers(
        transcript_segments, 
        audio_bytes,
        speaker_profile=speaker_profile
    )
    
    inference_time = time.time() - t_inf
    latency = time.time() - t0
    peak_ram = process.memory_info().peak_wset / (1024 * 1024) if hasattr(process.memory_info(), 'peak_wset') else process.memory_info().rss / (1024 * 1024)
    
    segments = []
    for s in transcript_segments:
        segments.append(Segment(start=s.start, end=s.end, speaker=s.speaker or "UNKNOWN", text=s.text))
        
    return create_neutral_output(
        pipeline_name="production_variant_c",
        sample_id=Path(wav_path).name,
        segments=segments,
        latency_seconds=latency,
        load_seconds=load_time,
        inference_seconds=inference_time,
        peak_ram_mb=peak_ram
    )

if __name__ == "__main__":
    wav_path = sys.argv[1]
    out_path = sys.argv[2]
    hf_token = os.environ.get("HF_TOKEN", "")
    
    res = asyncio.run(run_production(wav_path, hf_token))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
