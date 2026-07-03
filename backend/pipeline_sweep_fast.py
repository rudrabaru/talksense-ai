"""
TalkSense AI — Fast Pipeline Parameter Sweep Tool

Simulates the real-time streaming pipeline (250ms chunks, VAD, AudioBuffer,
Whisper, Pyannote) across two representative benchmark samples to quickly
evaluate parameter configurations.
"""

import json
import os
import subprocess
import sys
import time

import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audio.buffer as audio_buffer
from audio.buffer import AudioBuffer
from audio.diarizer import get_diarizer
from audio.transcriber import get_transcriber
from audio.vad import get_vad
from core.config import get_settings
from evaluate_speaker_accuracy import Segment as EvalSegment
from evaluate_speaker_accuracy import (
    compute_accuracy,
    compute_precision_recall_f1,
    compute_scdr,
    load_ground_truth,
    match_segments,
    resolve_label_mapping,
)

SAMPLE_RATE = 16000
DATASET_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "benchmark_dataset"
)
AUDIO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_audio")
)

# Select two representative samples (clean business meeting and conversational sales
# audio)
SELECTED_SAMPLES = ["2_speaker/meeting_short", "2_speaker/sales_ambiguous"]


def decode_audio(path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    pcm = proc.stdout.read()
    proc.wait()
    return pcm


def run_simulation(audio_path, expected_speakers, transcriber, diarizer, vad):
    pcm = decode_audio(audio_path)
    buffer = AudioBuffer()
    buffer._session_id = "sweep_sim_fast"

    chunk_size = 8000
    offset = 0
    all_diarized = []
    prev_speaker = "Speaker 1"

    while offset < len(pcm):
        chunk = pcm[offset : offset + chunk_size]
        offset += len(chunk)
        if not chunk:
            break

        is_speech = vad.is_speech(chunk)
        flushed_data = buffer.push(chunk, is_speech)

        if flushed_data:
            flushed, time_offset, is_partial = flushed_data
            raw_segs = transcriber.transcribe(flushed, time_offset=time_offset)
            if raw_segs:
                diarized = diarizer.assign_speakers(
                    raw_segs, flushed, time_offset, prev_speaker
                )
                if diarized:
                    prev_speaker = diarized[-1].speaker
                    all_diarized.extend(diarized)

    # Force flush remaining
    flushed_data = buffer.flush_remaining()
    if flushed_data:
        flushed, time_offset, is_partial = flushed_data
        raw_segs = transcriber.transcribe(flushed, time_offset=time_offset)
        if raw_segs:
            diarized = diarizer.assign_speakers(
                raw_segs, flushed, time_offset, prev_speaker
            )
            if diarized:
                all_diarized.extend(diarized)

    return all_diarized


def main():
    print("=" * 70)
    print("  TALKSENSE AI — FAST PIPELINE PARAMETER SWEEP")
    print("=" * 70)
    sys.stdout.flush()

    settings = get_settings()

    # Load Models
    print("Loading models...")
    sys.stdout.flush()
    transcriber = get_transcriber()
    transcriber.load(
        settings.whisper_model, settings.whisper_compute_type, settings.whisper_device
    )

    diarizer = get_diarizer()
    diarizer.load(settings.hf_token, settings.pyannote_device)

    vad = get_vad()

    # Discover samples
    samples = []
    for rel_path in SELECTED_SAMPLES:
        sample_dir = os.path.join(DATASET_ROOT, rel_path)
        if os.path.isdir(sample_dir) and os.path.isfile(
            os.path.join(sample_dir, "ground_truth.json")
        ):
            samples.append(sample_dir)

    print(f"Loaded {len(samples)} representative sweep samples.")
    sys.stdout.flush()

    # Define Sweep Axes
    durations = [1600, 1800, 2000]
    vad_thresholds = [0.55, 0.60, 0.65]

    sweep_results = []

    # Back up original buffer params
    orig_target_duration = audio_buffer.TARGET_DURATION_MS
    orig_min_flush = audio_buffer.MIN_FLUSH_MS

    # Run Sweep
    for target_dur in durations:
        for vad_thresh in vad_thresholds:
            print(
                f"\n--- Running Sweep: TARGET_DURATION={target_dur}ms, "
                f"VAD_THRESHOLD={vad_thresh} ---"
            )
            sys.stdout.flush()

            # Configure constants dynamically
            audio_buffer.TARGET_DURATION_MS = target_dur
            audio_buffer.MIN_FLUSH_MS = min(800, target_dur // 2)
            vad.threshold = vad_thresh

            f1_scores = []
            accuracy_scores = []
            scdr_scores = []

            t0 = time.monotonic()
            for sample_dir in samples:
                gt_path = os.path.join(sample_dir, "ground_truth.json")
                annotated, meta = load_ground_truth(gt_path)
                audio_path = os.path.join(AUDIO_DIR, meta["recording"])

                if not os.path.exists(audio_path):
                    continue

                # Run simulated streaming
                try:
                    predicted = run_simulation(
                        audio_path,
                        meta["expected_speakers"],
                        transcriber,
                        diarizer,
                        vad,
                    )
                except Exception as e:
                    print(f"  Error on {meta['recording']}: {e}")
                    sys.stdout.flush()
                    continue

                if not predicted:
                    continue

                # Evaluate
                pred_eval = [
                    EvalSegment(
                        start=s.start, end=s.end, speaker=s.speaker, text=s.text
                    )
                    for s in predicted
                ]
                pairs = match_segments(pred_eval, annotated, min_overlap_ratio=0.10)
                if pairs:
                    label_map = resolve_label_mapping(pairs)
                    accuracy, _, _ = compute_accuracy(pairs, label_map)
                    per_speaker = compute_precision_recall_f1(pairs, label_map)
                    scdr, _, _, _, _ = compute_scdr(pred_eval, annotated, label_map)
                    macro_f1 = (
                        sum(v["f1"] for v in per_speaker.values()) / len(per_speaker)
                        if per_speaker
                        else 0.0
                    )

                    f1_scores.append(macro_f1)
                    accuracy_scores.append(accuracy)
                    scdr_scores.append(scdr)

            elapsed = time.monotonic() - t0

            # Calculate averages
            avg_f1 = np.mean(f1_scores) if f1_scores else 0.0
            avg_acc = np.mean(accuracy_scores) if accuracy_scores else 0.0
            avg_scdr = np.mean(scdr_scores) if scdr_scores else 0.0

            print(
                f"Sweep Result: F1={avg_f1:.4f} | Accuracy={avg_acc:.1f}% | "
                f"SCDR={avg_scdr:.1f}% | Time={elapsed:.1f}s"
            )
            sys.stdout.flush()

            sweep_results.append(
                {
                    "target_duration_ms": target_dur,
                    "vad_threshold": vad_thresh,
                    "avg_macro_f1": round(avg_f1, 4),
                    "avg_accuracy": round(avg_acc, 1),
                    "avg_scdr": round(avg_scdr, 1),
                    "time_s": round(elapsed, 1),
                }
            )

    # Restore original constants
    audio_buffer.TARGET_DURATION_MS = orig_target_duration
    audio_buffer.MIN_FLUSH_MS = orig_min_flush

    # Save sweep results
    out_path = os.path.join(os.path.dirname(__file__), "sweep_results_fast.json")
    with open(out_path, "w") as f:
        json.dump(sweep_results, f, indent=2)
    print(f"\nSweep completed! Results saved to {out_path}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
