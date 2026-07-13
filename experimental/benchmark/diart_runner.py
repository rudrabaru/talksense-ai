import os
import subprocess
import json
import time
from pathlib import Path
import sys

# Add project root to path so we can import backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experimental.benchmark.common_schema import Segment, create_neutral_output
from experimental.benchmark.config import DIART_IMAGE, DIART_DEVICE, PROJECT_ROOT

def run_diart(wav_path: str, hf_token: str) -> dict:
    wav_path_obj = Path(wav_path).resolve()
    
    # We will mount the directory of the wav file
    wav_dir = wav_path_obj.parent
    wav_name = wav_path_obj.name
    
    out_dir = PROJECT_ROOT / "experimental" / "diart" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "result.json"
    
    if out_file.exists():
        out_file.unlink()
        
    cmd = [
        "docker", "run", "--rm",
        "-e", f"HF_TOKEN={hf_token}",
        "-v", f"{wav_dir}:/data:ro",
        "-v", f"{out_dir}:/out",
        DIART_IMAGE,
        f"/data/{wav_name}",
        "/out/result.json",
        "--device", DIART_DEVICE
    ]
    
    t0 = time.time()
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        print(f"Docker failed: {e.output}")
        raise
        
    latency = time.time() - t0
    
    with open(out_file, "r", encoding="utf-8") as f:
        raw_res = json.load(f)
        
    segments = []
    for s in raw_res.get("segments", []):
        segments.append(Segment(start=s["start"], end=s["end"], speaker=s["speaker"]))
        
    # The container reports its own latency if we want it, but total docker time is also useful.
    # We use container's latency if available, else total.
    container_latency = raw_res.get("inference_latency_seconds", latency)
    
    return create_neutral_output(
        pipeline_name="diart_experimental",
        sample_id=wav_name,
        segments=segments,
        latency_seconds=container_latency,
        metadata={"docker_overhead_seconds": latency - container_latency}
    )

if __name__ == "__main__":
    wav_path = sys.argv[1]
    out_path = sys.argv[2]
    hf_token = os.environ.get("HF_TOKEN", "")
    
    res = run_diart(wav_path, hf_token)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
