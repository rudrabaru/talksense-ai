"""
TalkSense AI -- Speaker Attribution Recovery Harness

Single-command evaluation with Pyannote parameter sweep.

Usage:
    python backend/speaker_recovery_harness.py

Tests multiple Pyannote configurations against ground truth and produces
a comparison table with the best configuration recommendation.
"""
import json
import os
import subprocess
import sys
import time
import wave
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SAMPLE_RATE = 16000
GT_PATH = os.path.join(os.path.dirname(__file__), "backend", "ground_truth", "meeting_short_gt.json")
AUDIO_PATH = os.path.join(os.path.dirname(__file__), "sample_audio", "meeting_short.mp3")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "backend", "speaker_recovery_results.json")


def decode_audio(audio_path):
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pcm = proc.stdout.read()
    proc.wait()
    return pcm


def load_gt(path):
    from backend.evaluate_speaker_accuracy import load_ground_truth
    return load_ground_truth(path)


def evaluate(predicted_segs, annotated_segs):
    from backend.evaluate_speaker_accuracy import (
        match_segments, resolve_label_mapping,
        compute_accuracy, compute_precision_recall_f1, compute_scdr,
        collect_failures, Segment as EvalSegment,
    )
    pairs = match_segments(predicted_segs, annotated_segs, min_overlap_ratio=0.10)
    if not pairs:
        return {
            "segments_matched": 0, "total_annotated": len(annotated_segs),
            "accuracy": 0.0, "macro_f1": 0.0, "scdr": 0.0,
            "per_speaker": {}, "label_map": {}, "failures": [],
            "speakers_detected": 0,
        }
    label_map = resolve_label_mapping(pairs)
    accuracy, correct, total = compute_accuracy(pairs, label_map)
    per_speaker = compute_precision_recall_f1(pairs, label_map)
    scdr, scdr_det, scdr_total = compute_scdr(predicted_segs, annotated_segs, label_map)
    macro_f1 = sum(v["f1"] for v in per_speaker.values()) / len(per_speaker) if per_speaker else 0.0
    failures = collect_failures(pairs, label_map)
    speakers = set(s.speaker for s in predicted_segs)
    return {
        "segments_matched": len(pairs), "total_annotated": len(annotated_segs),
        "accuracy": round(accuracy, 1), "correct": correct, "total_matched": total,
        "macro_f1": round(macro_f1, 4), "scdr": round(scdr, 1),
        "scdr_detected": scdr_det, "scdr_total": scdr_total,
        "per_speaker": per_speaker, "label_map": {k: v for k, v in label_map.items()},
        "failures": failures, "speakers_detected": len(speakers),
    }


def run_config(pipeline, pcm_data, transcriber, annotated_segs, config_name, pyannote_params):
    """Run a single Pyannote configuration and return metrics."""
    import torch
    from backend.evaluate_speaker_accuracy import Segment as EvalSegment

    # Transcribe full audio
    raw_segments = transcriber.transcribe(pcm_data, time_offset=0.0)
    if not raw_segments:
        return {"config": config_name, "error": "No segments from Whisper"}

    # Run Pyannote with specific params
    audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
    waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

    t0 = time.monotonic()
    diarization = pipeline(waveform, **pyannote_params)
    elapsed = time.monotonic() - t0

    # Unwrap
    try:
        from pyannote.audio.pipelines.speaker_diarization import DiarizeOutput
        if isinstance(diarization, DiarizeOutput):
            annotation = diarization.speaker_diarization
        else:
            annotation = diarization
    except ImportError:
        annotation = diarization

    # Build turns
    turns = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        mapped = speaker
        if speaker.startswith("SPEAKER_"):
            try:
                num = int(speaker.split("_")[-1])
                mapped = f"Speaker {num + 1}"
            except (ValueError, IndexError):
                pass
        turns.append((turn.start, turn.end, mapped))

    # Assign to Whisper segments
    predicted = []
    for seg in raw_segments:
        best_speaker, best_overlap = "Speaker 1", 0.0
        for t_s, t_e, spk in turns:
            ov = min(seg.end, t_e) - max(seg.start, t_s)
            if ov > best_overlap:
                best_overlap = ov
                best_speaker = spk
        predicted.append(EvalSegment(start=seg.start, end=seg.end, speaker=best_speaker, text=seg.text))

    metrics = evaluate(predicted, annotated_segs)
    metrics["config"] = config_name
    metrics["params"] = {k: str(v) for k, v in pyannote_params.items()}
    metrics["pyannote_time_s"] = round(elapsed, 2)
    metrics["turns_detected"] = len(turns)
    return metrics


def main():
    print("=" * 70)
    print("  TALKSENSE AI -- SPEAKER ATTRIBUTION RECOVERY HARNESS")
    print("=" * 70)

    # Load models
    from backend.core.config import get_settings
    from backend.audio.transcriber import get_transcriber
    settings = get_settings()

    print("\n[1/4] Loading Whisper...")
    transcriber = get_transcriber()
    transcriber.load(settings.whisper_model, settings.whisper_compute_type, settings.whisper_device)

    print("[2/4] Loading Pyannote pipeline...")
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*torchcodec.*", category=UserWarning)
        from pyannote.audio import Pipeline
    import torch
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=settings.hf_token,
    )
    pipeline.to(torch.device(settings.pyannote_device))
    print("  Pipeline loaded.")

    print("[3/4] Decoding audio...")
    pcm_data = decode_audio(AUDIO_PATH)
    duration = len(pcm_data) / 2 / SAMPLE_RATE
    print(f"  PCM: {len(pcm_data)} bytes ({duration:.1f}s)")

    print("[4/4] Loading ground truth...")
    annotated_segs, metadata = load_gt(GT_PATH)
    print(f"  {len(annotated_segs)} segments, {metadata['expected_speakers']} speakers")

    # ── PARAMETER SWEEP ───────────────────────────────────────────────────────
    # Access pipeline hyperparameters to understand what we can tune
    print("\n" + "=" * 70)
    print("  PARAMETER SWEEP")
    print("=" * 70)

    configs = [
        ("A: default (no hints)", {}),
        ("B: num_speakers=2", {"num_speakers": 2}),
        ("C: min_speakers=2, max_speakers=2", {"min_speakers": 2, "max_speakers": 2}),
        ("D: min_speakers=2, max_speakers=3", {"min_speakers": 2, "max_speakers": 3}),
        ("E: num_speakers=3", {"num_speakers": 3}),
    ]

    # Try to tune clustering threshold and min_duration_off if accessible
    try:
        params = pipeline.parameters(instantiated=True)
        print(f"\n  Pipeline parameters: {list(params.keys()) if isinstance(params, dict) else 'opaque'}")
    except Exception:
        print("\n  Could not inspect pipeline parameters (expected for Pyannote 3.1)")

    all_results = []

    for i, (name, params) in enumerate(configs):
        print(f"\n  [{i+1}/{len(configs)}] Running: {name}")
        print(f"    Params: {params}")
        try:
            result = run_config(pipeline, pcm_data, transcriber, annotated_segs, name, params)
            all_results.append(result)
            print(f"    Speakers: {result.get('speakers_detected', '?')}")
            print(f"    Turns:    {result.get('turns_detected', '?')}")
            print(f"    F1:       {result.get('macro_f1', '?')}")
            print(f"    SCDR:     {result.get('scdr', '?')}%")
            print(f"    Accuracy: {result.get('accuracy', '?')}%")
            print(f"    Time:     {result.get('pyannote_time_s', '?')}s")
        except Exception as e:
            print(f"    ERROR: {e}")
            all_results.append({"config": name, "error": str(e)})

    # ── COMPARISON TABLE ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  COMPARISON TABLE")
    print("=" * 70)

    header = f"  {'Config':<42} {'Spk':>3} {'Turns':>5} {'F1':>6} {'SCDR':>6} {'Acc':>6} {'Time':>5}"
    print(header)
    print("  " + "-" * 68)

    best_config = None
    best_f1 = -1.0

    for r in all_results:
        if "error" in r:
            print(f"  {r['config']:<42} ERROR: {r['error'][:30]}")
            continue
        line = (
            f"  {r['config']:<42} "
            f"{r.get('speakers_detected', '?'):>3} "
            f"{r.get('turns_detected', '?'):>5} "
            f"{r.get('macro_f1', 0):>6.3f} "
            f"{r.get('scdr', 0):>5.1f}% "
            f"{r.get('accuracy', 0):>5.1f}% "
            f"{r.get('pyannote_time_s', 0):>5.1f}s"
        )
        print(line)

        f1 = r.get("macro_f1", 0)
        scdr = r.get("scdr", 0)
        # Prefer config with highest combined score (weighted F1 + SCDR)
        score = f1 * 0.6 + (scdr / 100) * 0.4
        if score > best_f1:
            best_f1 = score
            best_config = r

    # ── RECOMMENDATION ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RECOMMENDATION")
    print("=" * 70)

    if best_config:
        print(f"  Best config: {best_config['config']}")
        print(f"  Macro F1:    {best_config.get('macro_f1', 0):.3f} (threshold: 0.750)")
        print(f"  SCDR:        {best_config.get('scdr', 0):.1f}% (threshold: 70.0%)")
        print(f"  Accuracy:    {best_config.get('accuracy', 0):.1f}%")

        passes_f1 = best_config.get("macro_f1", 0) >= 0.75
        passes_scdr = best_config.get("scdr", 0) >= 70.0

        if passes_f1 and passes_scdr:
            print("  VERDICT: [PASS] - Production ready with this configuration")
        else:
            gaps = []
            if not passes_f1:
                gaps.append(f"F1 gap: {0.75 - best_config.get('macro_f1', 0):.3f}")
            if not passes_scdr:
                gaps.append(f"SCDR gap: {70.0 - best_config.get('scdr', 0):.1f}pp")
            print(f"  VERDICT: [FAIL] - {', '.join(gaps)}")

    # ── SAVE RESULTS ──────────────────────────────────────────────────────────
    output = {
        "audio": AUDIO_PATH,
        "ground_truth": GT_PATH,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "configs": all_results,
        "best_config": best_config["config"] if best_config else None,
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {REPORT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
