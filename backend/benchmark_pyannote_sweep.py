import os
import time
import json
import numpy as np
import torch
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)
    try:
        from pyannote.audio import Pipeline
    except RuntimeError as e:
        print(f"Caught Pyannote import error: {e}")
        import sys; sys.exit(1)

def measure_peak_vram():
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / (1024 ** 2)
    return 0.0

def main():
    print("Loading Pyannote...")
    t0 = time.monotonic()
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        # try reading from .env
        from dotenv import load_dotenv
        load_dotenv()
        hf_token = os.environ.get("HF_TOKEN")
        
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=hf_token)
    pipeline.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Loaded in {time.monotonic() - t0:.1f}s")

    sample_rate = 16000
    duration = 60.0 # 60 seconds
    print(f"Creating {duration}s dummy audio tensor...")
    waveform = torch.randn(1, int(sample_rate * duration))
    audio_dict = {"waveform": waveform, "sample_rate": sample_rate}

    # Warm-up
    print("Running warm-up...")
    dummy = torch.zeros(1, sample_rate * 2)
    with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.float16):
        _ = pipeline({"waveform": dummy, "sample_rate": sample_rate}, num_speakers=2)
    print("Warm-up done.")

    strides = [0.10, 0.15, 0.20, 0.25]
    batch_sizes = [1, 2, 4, 8, 32]
    
    results = []
    
    for stride in strides:
        for batch in batch_sizes:
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.empty_cache()
                
            print(f"\nEvaluating Stride={stride}, Batch={batch}...")
            
            pipeline.segmentation_step = stride
            pipeline.segmentation_batch_size = batch
            
            t_start = time.monotonic()
            with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.float16):
                diarization = pipeline(audio_dict, num_speakers=2)
            t_end = time.monotonic()
            
            latency = (t_end - t_start) * 1000
            vram = measure_peak_vram()
            
            # Simple hash of boundaries to detect drift
            annotation = getattr(diarization, "speaker_diarization", diarization)
            turn_count = len(list(annotation.itertracks()))
            
            print(f"  Latency: {latency:.1f}ms")
            print(f"  Peak VRAM: {vram:.1f} MB")
            print(f"  Turns generated: {turn_count}")
            
            results.append({
                "stride": stride,
                "batch_size": batch,
                "latency_ms": latency,
                "peak_vram_mb": vram,
                "turns": turn_count
            })
            
    # Print Markdown Table
    print("\n\n### Results")
    print("| Stride | Batch | Latency (ms) | Peak VRAM (MB) | Turns |")
    print("|---|---|---|---|---|")
    for r in results:
        print(f"| {r['stride']} | {r['batch_size']} | {r['latency_ms']:.1f} | {r['peak_vram_mb']:.1f} | {r['turns']} |")
        
if __name__ == "__main__":
    main()
