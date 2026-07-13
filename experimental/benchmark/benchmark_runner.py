import os
import sys
import json
import time
import subprocess
import csv
import statistics
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from experimental.benchmark.config import DATASET_DIR, REPORTS_DIR, PROJECT_ROOT
from experimental.benchmark.common_schema import Segment
from experimental.benchmark.evaluator import (
    match_segments, resolve_label_mapping, compute_accuracy,
    compute_precision_recall_f1, compute_scdr
)

def get_wav_files():
    wavs = []
    for mode in ["interview", "meeting", "sales"]:
        mode_dir = DATASET_DIR / mode
        if mode_dir.exists():
            wavs.extend([(wav, mode) for wav in mode_dir.glob("*.wav")])
    return wavs

def parse_segments(raw_json: dict) -> list[Segment]:
    segments = []
    for s in raw_json.get("segments", []):
        segments.append(Segment(start=s["start"], end=s["end"], speaker=s["speaker"]))
    return segments

def safe_run(cmd, env):
    try:
        res = subprocess.run(cmd, check=True, env=env, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return True, res.stdout
    except subprocess.CalledProcessError as e:
        return False, e.output
    except Exception as e:
        return False, str(e)

def run_benchmark():
    wavs = get_wav_files()
    if not wavs:
        print("No WAV files found in dataset directories.")
        return

    python_exe = str(PROJECT_ROOT / "backend" / "venv" / "Scripts" / "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    prod_runner = str(Path(__file__).parent / "production_runner.py")
    diart_runner = str(Path(__file__).parent / "diart_runner.py")
    
    outputs_dir = REPORTS_DIR.parent / "outputs"
    os.makedirs(outputs_dir / "production", exist_ok=True)
    os.makedirs(outputs_dir / "diart", exist_ok=True)
    
    results = []
    
    env = os.environ.copy()
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN environment variable is not set.")
    env["HF_TOKEN"] = hf_token

    print(f"Found {len(wavs)} recordings. Starting benchmark...")
    
    for wav, category in wavs:
        print(f"[{category}] Benchmarking {wav.name}...")
        
        prod_out = outputs_dir / "production" / f"{wav.stem}.json"
        diart_out = outputs_dir / "diart" / f"{wav.stem}.json"
        
        # Production
        print("  -> Running Production (Variant C)...")
        prod_ok, prod_err = safe_run([python_exe, prod_runner, str(wav), str(prod_out)], env)
        
        # Diart
        print("  -> Running Diart (Experimental)...")
        diart_ok, diart_err = safe_run([sys.executable, diart_runner, str(wav), str(diart_out)], env)
        
        if not prod_ok or not diart_ok:
            print(f"  -> FAILURE on {wav.name}")
            results.append({
                "file": wav.name,
                "category": category,
                "status": "failed",
                "error": (prod_err if not prod_ok else "") + "\n" + (diart_err if not diart_ok else "")
            })
            continue

        try:
            with open(prod_out, "r", encoding="utf-8") as f: prod_data = json.load(f)
            with open(diart_out, "r", encoding="utf-8") as f: diart_data = json.load(f)
                
            prod_segs = parse_segments(prod_data)
            diart_segs = parse_segments(diart_data)
            
            pairs = match_segments(predicted=diart_segs, annotated=prod_segs, min_overlap_ratio=0.10)
            label_map = resolve_label_mapping(pairs)
            
            acc, correct, total = compute_accuracy(pairs, label_map)
            prf1 = compute_precision_recall_f1(pairs, label_map)
            scdr, scdr_det, scdr_tot = compute_scdr(diart_segs, prod_segs, label_map)
            
            macro_f1 = sum(v["f1"] for v in prf1.values()) / len(prf1) if prf1 else 0.0
            
            prod_duration = sum(s.duration() for s in prod_segs)
            diart_duration = sum(s.duration() for s in diart_segs)
            
            p_switch = len([i for i in range(1, len(prod_segs)) if prod_segs[i].speaker != prod_segs[i-1].speaker])
            d_switch = len([i for i in range(1, len(diart_segs)) if diart_segs[i].speaker != diart_segs[i-1].speaker])
            
            p_frag = len(prod_segs) / max(1.0, prod_duration)
            d_frag = len(diart_segs) / max(1.0, diart_duration)
            
            results.append({
                "file": wav.name,
                "category": category,
                "status": "success",
                "prod_speakers": len(prod_data["speakers"]),
                "diart_speakers": len(diart_data["speakers"]),
                "prod_segments": len(prod_segs),
                "diart_segments": len(diart_segs),
                "prod_duration": prod_duration,
                "diart_duration": diart_duration,
                "prod_switch_count": p_switch,
                "diart_switch_count": d_switch,
                "prod_frag_ratio": p_frag,
                "diart_frag_ratio": d_frag,
                "acc_percent": acc,
                "macro_f1": macro_f1,
                "scdr_percent": scdr,
                "prod_latency": prod_data["runtime"]["latency_seconds"],
                "diart_latency": diart_data["runtime"]["latency_seconds"],
                "prod_load": prod_data["runtime"].get("load_seconds", 0.0),
                "diart_load": diart_data["runtime"].get("load_seconds", 0.0),
                "prod_inference": prod_data["runtime"].get("inference_seconds", 0.0),
                "diart_inference": diart_data["runtime"].get("inference_seconds", 0.0),
                "prod_peak_ram": prod_data["runtime"].get("peak_ram_mb", 0.0),
                "diart_peak_ram": diart_data["runtime"].get("peak_ram_mb", 0.0),
            })
        except Exception as e:
            print(f"  -> VALIDATION FAILURE on {wav.name}: {e}")
            results.append({
                "file": wav.name,
                "category": category,
                "status": "validation_failed",
                "error": traceback.format_exc()
            })

    # Generate Reports
    generate_reports(results)

def generate_reports(results):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # JSON
    with open(REPORTS_DIR / "benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    # CSV
    if results:
        # Get all keys including ones that might be missing in failures
        all_keys = set()
        for r in results:
            all_keys.update(r.keys())
        keys = ["file", "category", "status"] + [k for k in all_keys if k not in ("file", "category", "status", "error")] + (["error"] if "error" in all_keys else [])
        
        with open(REPORTS_DIR / "benchmark_report.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)

    # Markdown (Basic for now)
    md = [
        "# TalkSense AI v4 — Experimental Benchmark Final Report",
        f"Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        "## Benchmark Limitations",
        "- The benchmark measures agreement with the production Variant C pipeline.",
        "- It does not measure absolute diarization accuracy because no independently annotated ground-truth dataset is currently available.",
        "- Any architectural recommendations should therefore be treated as preliminary until validated against ground truth.\n",
        "## Summary",
        f"Total Processed: {len(results)}",
        f"Successful: {sum(1 for r in results if r['status'] == 'success')}",
        f"Failed: {sum(1 for r in results if r['status'] != 'success')}\n"
    ]
    
    success_results = [r for r in results if r["status"] == "success"]
    if success_results:
        f1_scores = [r["macro_f1"] for r in success_results]
        md.extend([
            "## Aggregate Agreement Metrics",
            f"- Mean Macro F1: {statistics.mean(f1_scores):.3f}",
            f"- Median Macro F1: {statistics.median(f1_scores):.3f}",
            f"- Min Macro F1: {min(f1_scores):.3f}",
            f"- Max Macro F1: {max(f1_scores):.3f}"
        ])
        if len(f1_scores) > 1:
            md.append(f"- StdDev Macro F1: {statistics.stdev(f1_scores):.3f}")
            
    with open(REPORTS_DIR / "benchmark_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print(f"Benchmark complete. Reports in {REPORTS_DIR}")

if __name__ == "__main__":
    run_benchmark()
