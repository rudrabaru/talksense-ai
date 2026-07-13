import argparse
import json
import os
import sys
import time

import torch
import torchaudio
import pyannote.audio
import diart
from diart import SpeakerDiarization, SpeakerDiarizationConfig
from diart.sources import FileAudioSource
from diart.inference import StreamingInference
from diart.sinks import RTTMWriter

def parse_rttm(rttm_path):
    segments = []
    # RTTM format: SPEAKER uri 1 start duration <NA> <NA> speaker_id <NA> <NA>
    with open(rttm_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 8 and parts[0] == "SPEAKER":
                start = float(parts[3])
                duration = float(parts[4])
                speaker_id = parts[7]
                segments.append({
                    "start": start,
                    "end": start + duration,
                    "speaker": speaker_id
                })
    return segments

def main():
    parser = argparse.ArgumentParser(description="Diart inference minimal CLI")
    parser.add_argument("input_wav", help="Absolute path to input WAV")
    parser.add_argument("output_json", help="Absolute path to output JSON")
    parser.add_argument("--device", default=None, help="cpu or cuda")
    args = parser.parse_args()

    input_wav = args.input_wav
    output_json = args.output_json

    if not os.path.isfile(input_wav):
        print(f"Error: input file {input_wav} not found.", file=sys.stderr)
        sys.exit(1)
        
    try:
        info = torchaudio.info(input_wav)
        duration_seconds = info.num_frames / info.sample_rate
        sample_rate = info.sample_rate
    except Exception as e:
        print(f"Error reading WAV: {e}", file=sys.stderr)
        sys.exit(1)

    device_str = args.device
    if device_str is None:
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
    
    device = torch.device(device_str)
    
    t0 = time.monotonic()
    
    try:
        config = SpeakerDiarizationConfig(
            duration=3.0,
            step=0.5,
            latency=0.5,
            tau_active=0.6,
            rho_update=0.3,
            delta_new=1.0,
            device=device
        )
        pipeline = SpeakerDiarization(config)
    except Exception as e:
        print(f"Error initializing Diart: {e}", file=sys.stderr)
        sys.exit(1)

    t_init = time.monotonic()
    
    try:
        source = FileAudioSource(input_wav, sample_rate=16000)
        rttm_path = "/tmp/out.rttm"
        inference = StreamingInference(pipeline, source, do_plot=False)
        inference.attach_observers(RTTMWriter(source.uri, rttm_path))
        inference()
        
        raw_segments = parse_rttm(rttm_path)
    except Exception as e:
        print(f"Error during inference: {e}", file=sys.stderr)
        sys.exit(1)

    t_inf = time.monotonic()
    inference_latency = t_inf - t_init
    load_latency = t_init - t0
    
    import resource
    peak_ram = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 # in MB

    # Normalize labels (first encountered -> SPEAKER_00, etc)
    speaker_map = {}
    normalized_segments = []
    
    for seg in raw_segments:
        raw_spk = seg["speaker"]
        if raw_spk not in speaker_map:
            speaker_map[raw_spk] = f"SPEAKER_{len(speaker_map):02d}"
        
        # Clamp bounds
        start = max(0.0, float(seg["start"]))
        end = min(duration_seconds, float(seg["end"]))
        
        if end > start:
            normalized_segments.append({
                "speaker": speaker_map[raw_spk],
                "start": round(start, 3),
                "end": round(end, 3)
            })

    output_data = {
        "schema_version": "1.0",
        "sample_id": os.path.basename(input_wav),
        "backend": "diart",
        "diart_version": "0.9.2",
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "pyannote_version": "3.1.1",
        "device": device_str,
        "sample_rate": sample_rate,
        "duration_seconds": round(duration_seconds, 3),
        "inference_latency_seconds": round(inference_latency, 3),
        "load_latency_seconds": round(load_latency, 3),
        "peak_ram_mb": round(peak_ram, 2),
        "error_state": None,
        "segments": normalized_segments
    }

    try:
        with open(output_json, "w") as f:
            json.dump(output_data, f, indent=2)
    except Exception as e:
        print(f"Error writing output JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print("Success")
    sys.exit(0)

if __name__ == "__main__":
    main()
