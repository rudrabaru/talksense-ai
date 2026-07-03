"""
TalkSense AI — Full Benchmark Runner

Runs speaker attribution evaluation across the entire benchmark dataset.

Usage:
    python backend/run_full_benchmark.py

Pipeline per sample:
    1. Decode audio to PCM
    2. Transcribe with Whisper (full audio, single pass)
    3. Diarize with Pyannote (num_speakers from GT metadata)
    4. Assign speakers to Whisper segments via max-overlap
    5. Evaluate against ground truth
    6. Aggregate across all samples

Outputs:
    backend/benchmark_results.json — per-sample and aggregate metrics
"""

import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SAMPLE_RATE = 16000
DATASET_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "benchmark_dataset"
)
AUDIO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_audio")
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "benchmark_results.json"
)
ERROR_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "scdr_error_log.json"
)
CATEGORIES = ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]

# Thresholds
THRESHOLD_F1 = 0.75
THRESHOLD_ACCURACY = 0.80
THRESHOLD_SCDR = 0.70


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


def run_sample(pipeline, transcriber, sample_dir, audio_dir):
    """Run diarization + evaluation for a single benchmark sample."""
    import torch

    from evaluate_speaker_accuracy import (
        Segment as EvalSegment,
    )
    from evaluate_speaker_accuracy import (
        collect_failures,
        compute_accuracy,
        compute_precision_recall_f1,
        compute_scdr,
        match_segments,
        resolve_label_mapping,
    )

    gt_path = os.path.join(sample_dir, "ground_truth.json")
    meta_path = os.path.join(sample_dir, "metadata.json")

    with open(gt_path, "r", encoding="utf-8") as f:
        gt = json.load(f)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    audio_file = gt["recording"]
    audio_path = os.path.join(audio_dir, audio_file)
    expected_speakers = gt.get("expected_speakers", 2)

    if not os.path.isfile(audio_path):
        return {
            "error": f"Audio not found: {audio_path}",
            "sample": os.path.basename(sample_dir),
        }

    # Decode
    pcm = decode_audio(audio_path)
    duration = len(pcm) / 2 / SAMPLE_RATE

    # Transcribe
    t0 = time.monotonic()
    raw_segments = transcriber.transcribe(pcm, time_offset=0.0)
    print(f"  Transcription finished in {time.monotonic() - t0:.1f}s")
    whisper_time = time.monotonic() - t0

    if not raw_segments:
        raise RuntimeError(
            f"Whisper returned no segments for {audio_file}. Empty transcript failure."
        )

    # Diarize
    audio_int16 = np.frombuffer(pcm, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    # Phase 3: VAD Prefilter
    # Simply zero-out audio below a strict energy threshold if enabled
    if os.environ.get("STRICT_VAD_PREFILTER") == "1":
        # Simple energy-based strict VAD mock for benchmark
        frame_size = int(SAMPLE_RATE * 0.05)  # 50ms
        for i in range(0, len(audio_float32), frame_size):
            chunk = audio_float32[i : i + frame_size]
            if len(chunk) > 0 and np.mean(np.abs(chunk)) < 0.005:  # strict threshold
                audio_float32[i : i + frame_size] = 0.0

    audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
    waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

    step_val = os.environ.get("PYANNOTE_STEP")
    batch_val = os.environ.get("PYANNOTE_BATCH_SIZE")

    if step_val:
        pipeline.segmentation_step = float(step_val)
    if batch_val:
        pipeline.segmentation_batch_size = int(batch_val)

    # Apply Pyannote Configuration Overrides (Phase 1)
    params = {}
    if os.environ.get("PYANNOTE_MIN_DURATION_OFF"):
        params["segmentation"] = {
            "min_duration_off": float(os.environ["PYANNOTE_MIN_DURATION_OFF"])
        }
    if os.environ.get("PYANNOTE_CLUSTERING_THRESHOLD"):
        params["clustering"] = {
            "threshold": float(os.environ["PYANNOTE_CLUSTERING_THRESHOLD"])
        }

    if params:
        try:
            pipeline.instantiate(params)
        except Exception as e:
            print(f"Warning: Failed to instantiate Pyannote params {params}: {e}")

    t0 = time.monotonic()
    with torch.inference_mode():
        diarization = pipeline(waveform, num_speakers=expected_speakers)
    pyannote_time = time.monotonic() - t0

    # Unwrap DiarizeOutput wrapper if present (pyannote-audio 4.x) using duck-typing
    # to bypass class-identity mismatches under Uvicorn reload environments.
    annotation = getattr(diarization, "speaker_diarization", diarization)

    # Build turns
    turns = []
    short_filter_val = os.environ.get("FILTER_SHORT_UTTERANCES_S")
    short_filter_s = float(short_filter_val) if short_filter_val else 0.0

    for turn, _, speaker in annotation.itertracks(yield_label=True):
        mapped = speaker
        if speaker.startswith("SPEAKER_"):
            try:
                num = int(speaker.split("_")[-1])
                mapped = f"Speaker {num + 1}"
            except (ValueError, IndexError):
                pass

        # Phase 2: Short Utterance Filtering
        if (turn.end - turn.start) < short_filter_s:
            continue

        turns.append((turn.start, turn.end, mapped))

    predicted = []

    if os.environ.get("USE_SENTENCE_LEVEL_ALIGNMENT") == "1":
        # Sprint 12 Baseline: Sentence-level overlap
        for seg in raw_segments:
            seg_dur = seg.end - seg.start
            if seg_dur <= 0:
                continue

            best_speaker = "Speaker 1"
            max_overlap = -1.0

            for t_start, t_end, speaker in turns:
                overlap = max(0.0, min(seg.end, t_end) - max(seg.start, t_start))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker

            predicted.append(
                EvalSegment(
                    start=seg.start, end=seg.end, speaker=best_speaker, text=seg.text
                )
            )
    else:
        # Assign speakers using Sprint 13 architecture (word-level)
        from services.word_speaker_aligner import align_words_to_speakers

        all_words = []
        for seg in raw_segments:
            if getattr(seg, "words", None):
                for w in seg.words:
                    all_words.append(
                        {
                            "word": w.word,
                            "start": w.start,
                            "end": w.end,
                            "probability": getattr(
                                w, "probability", getattr(w, "confidence", 1.0)
                            ),
                        }
                    )
            else:
                all_words.append(
                    {
                        "word": seg.text,
                        "start": seg.start,
                        "end": seg.end,
                        "probability": getattr(seg, "avg_logprob", 1.0),
                    }
                )

        aligned_words = align_words_to_speakers(all_words, turns)

        predicted = []
        if aligned_words:
            current_speaker = aligned_words[0]["speaker"]
            current_words = []
            for w in aligned_words:
                # We break a segment if speaker changes OR if there's a gap > 1.0s
                gap = w["start"] - current_words[-1]["end"] if current_words else 0.0
                if w["speaker"] != current_speaker or gap > 1.0:
                    if current_words:
                        text = "".join(
                            x["word"] for x in current_words if x["word"].strip()
                        ).strip()
                        if not text:
                            text = " ".join(
                                x["word"].strip() for x in current_words
                            ).strip()
                        predicted.append(
                            EvalSegment(
                                start=current_words[0]["start"],
                                end=current_words[-1]["end"],
                                speaker=current_speaker,
                                text=text,
                            )
                        )
                    current_speaker = w["speaker"]
                    current_words = [w]
                else:
                    current_words.append(w)

            if current_words:
                text = "".join(
                    x["word"] for x in current_words if x["word"].strip()
                ).strip()
                if not text:
                    text = " ".join(x["word"].strip() for x in current_words).strip()
                predicted.append(
                    EvalSegment(
                        start=current_words[0]["start"],
                        end=current_words[-1]["end"],
                        speaker=current_speaker,
                        text=text,
                    )
                )

    # Post-processing: fix speaker fragmentation
    if os.environ.get("DISABLE_POSTPROCESSING") != "1":
        from config.diarization_postprocessing import apply_postprocessing

        predicted = apply_postprocessing(predicted)

    # Padding step to restore VAD-like boundaries for SCDR compatibility
    # SCDR uses the midpoint of gap between segments. Word-timestamps shrink segments,
    # moving the midpoint. We expand segments to meet at the Pyannote transition.
    # ONLY do this if using word-level alignment, since sentence-level inherently spans gaps.
    if os.environ.get("USE_SENTENCE_LEVEL_ALIGNMENT") != "1":
        for i in range(len(predicted) - 1):
            if predicted[i].speaker != predicted[i + 1].speaker:
                transition_time = None
                for j in range(len(turns) - 1):
                    # Check for Pyannote turn boundary matching this speaker change
                    if (
                        turns[j][2] == predicted[i].speaker
                        and turns[j + 1][2] == predicted[i + 1].speaker
                    ):
                        t = (turns[j][1] + turns[j + 1][0]) / 2
                        if predicted[i].start <= t <= predicted[i + 1].end:
                            transition_time = t
                            break

                if transition_time is not None:
                    # Force segments to meet at Pyannote transition so `midpoint` is correct
                    predicted[i].end = transition_time
                    predicted[i + 1].start = transition_time

    # Build GT segments
    annotated = [
        EvalSegment(
            start=s["start"], end=s["end"], speaker=s["speaker"], text=s.get("text", "")
        )
        for s in gt["segments"]
    ]

    # Evaluate
    pairs = match_segments(predicted, annotated, min_overlap_ratio=0.10)
    if not pairs:
        raise RuntimeError(
            f"No segments matched for {audio_file}. Ground truth timestamp mismatch."
        )

    label_map = resolve_label_mapping(pairs)
    accuracy, correct, total = compute_accuracy(pairs, label_map)
    per_speaker = compute_precision_recall_f1(pairs, label_map)
    scdr, scdr_det, scdr_total, scdr_errors, detailed = compute_scdr(
        predicted, annotated, label_map
    )
    macro_f1 = (
        sum(v["f1"] for v in per_speaker.values()) / len(per_speaker)
        if per_speaker
        else 0.0
    )
    failures = collect_failures(pairs, label_map, limit=99999)

    return {
        "sample": os.path.basename(sample_dir),
        "category": meta.get("category", "unknown"),
        "recording": audio_file,
        "duration_s": round(duration, 1),
        "segments_matched": len(pairs),
        "total_annotated": len(annotated),
        "total_predicted": len(predicted),
        "accuracy": round(accuracy, 1),
        "macro_f1": round(macro_f1, 4),
        "scdr": round(scdr, 1),
        "scdr_detected": scdr_det,
        "scdr_total": scdr_total,
        "scdr_errors_ms": scdr_errors,
        "scdr_detailed": detailed,
        "speakers_expected": expected_speakers,
        "speakers_detected": len(set(s.speaker for s in predicted)),
        "per_speaker": {
            k: {
                kk: round(vv, 4) if isinstance(vv, float) else vv
                for kk, vv in v.items()
            }
            for k, v in per_speaker.items()
        },
        "label_map": {k: v for k, v in label_map.items()},
        "failures": failures[:5],  # First 5 only
        "whisper_time_s": round(whisper_time, 1),
        "pyannote_time_s": round(pyannote_time, 1),
    }


def generate_report(results, output_path):
    """Generate benchmark_report.md from results."""
    report_path = output_path.replace(".json", "_report.md")
    lines = []
    lines.append("# TalkSense AI — Speaker Attribution Benchmark Report")
    lines.append(f"\n> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(
        f"> Thresholds: F1 >= {THRESHOLD_F1}, Accuracy >= {THRESHOLD_ACCURACY * 100}%, SCDR >= {THRESHOLD_SCDR * 100}%"  # noqa: E501
    )
    lines.append("")

    # Overall metrics
    valid = [r for r in results if "error" not in r and r.get("macro_f1") is not None]
    if valid:
        avg_f1 = sum(r["macro_f1"] for r in valid) / len(valid)
        avg_acc = sum(r["accuracy"] for r in valid) / len(valid)
        avg_scdr = sum(r["scdr"] for r in valid) / len(valid)
        total_duration = sum(r.get("duration_s", 0) for r in valid)

        lines.append("## Overall Metrics")
        lines.append("")
        lines.append("| Metric | Value | Threshold | Status |")
        lines.append("|--------|-------|-----------|--------|")
        lines.append(
            f"| Average Macro F1 | **{avg_f1:.4f}** | {THRESHOLD_F1} | {'PASS' if avg_f1 >= THRESHOLD_F1 else 'FAIL'} |"  # noqa: E501
        )
        lines.append(
            f"| Average Accuracy | **{avg_acc:.1f}%** | {THRESHOLD_ACCURACY * 100}% | {'PASS' if avg_acc / 100 >= THRESHOLD_ACCURACY else 'FAIL'} |"  # noqa: E501
        )
        lines.append(
            f"| Average SCDR | **{avg_scdr:.1f}%** | {THRESHOLD_SCDR * 100}% | {'PASS' if avg_scdr / 100 >= THRESHOLD_SCDR else 'FAIL'} |"  # noqa: E501
        )
        lines.append(f"| Samples Tested | {len(valid)} | - | - |")
        lines.append(
            f"| Total Audio | {total_duration:.0f}s ({total_duration / 60:.1f} min) | - | - |"  # noqa: E501
        )
        lines.append("")

        all_pass = (
            avg_f1 >= THRESHOLD_F1
            and avg_acc / 100 >= THRESHOLD_ACCURACY
            and avg_scdr / 100 >= THRESHOLD_SCDR
        )
        if all_pass:
            lines.append("> **PRODUCTION READY**")
        else:
            lines.append("> **NOT PRODUCTION READY**")
        lines.append("")

    # Per-category metrics
    lines.append("---")
    lines.append("")
    lines.append("## Per-Category Metrics")
    lines.append("")

    categories = {}
    for r in valid:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    lines.append("| Category | Samples | Avg F1 | Avg Accuracy | Avg SCDR | Status |")
    lines.append("|----------|---------|--------|-------------|----------|--------|")

    for cat in sorted(categories.keys()):
        cat_results = categories[cat]
        cf1 = sum(r["macro_f1"] for r in cat_results) / len(cat_results)
        cacc = sum(r["accuracy"] for r in cat_results) / len(cat_results)
        cscdr = sum(r["scdr"] for r in cat_results) / len(cat_results)
        status = (
            "PASS"
            if cf1 >= THRESHOLD_F1
            and cacc / 100 >= THRESHOLD_ACCURACY
            and cscdr / 100 >= THRESHOLD_SCDR
            else "FAIL"
        )
        lines.append(
            f"| {cat} | {len(cat_results)} | {cf1:.4f} | {cacc:.1f}% | {cscdr:.1f}% | {status} |"  # noqa: E501
        )

    lines.append("")

    # Per-sample metrics
    lines.append("---")
    lines.append("")
    lines.append("## Per-Sample Metrics")
    lines.append("")
    lines.append(
        "| Sample | Category | Duration | Spk Expected | Spk Detected | F1 | SCDR | Acc | Status |"  # noqa: E501
    )
    lines.append(
        "|--------|----------|----------|-------------|-------------|------|------|------|--------|"
    )

    for r in sorted(valid, key=lambda x: x.get("category", "")):
        status = (
            "PASS"
            if r["macro_f1"] >= THRESHOLD_F1
            and r["accuracy"] / 100 >= THRESHOLD_ACCURACY
            and r["scdr"] / 100 >= THRESHOLD_SCDR
            else "FAIL"
        )
        lines.append(
            f"| {r['sample']} | {r.get('category', '-')} | {r.get('duration_s', 0):.0f}s | "  # noqa: E501
            f"{r.get('speakers_expected', '?')} | {r.get('speakers_detected', '?')} | "
            f"{r['macro_f1']:.3f} | {r['scdr']:.0f}% | {r['accuracy']:.0f}% | {status} |"  # noqa: E501
        )

    # Errors
    errored = [r for r in results if "error" in r]
    if errored:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for r in errored:
            lines.append(f"- **{r.get('sample', 'unknown')}**: {r['error']}")

    lines.append("")

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report_path


def main():
    import warnings

    print("=" * 70)
    print("  TALKSENSE AI — FULL BENCHMARK RUNNER")
    print("=" * 70)

    if not os.path.isdir(DATASET_ROOT):
        print(f"\n  ERROR: Dataset not found: {DATASET_ROOT}")
        print("  Run the dataset setup first.")
        sys.exit(1)

    # Load models
    import torch

    from audio.transcriber import get_transcriber
    from core.config import get_settings

    settings = get_settings()

    print("\n[1/3] Loading Whisper...")
    transcriber = get_transcriber()
    transcriber.load(
        settings.whisper_model, settings.whisper_compute_type, settings.whisper_device
    )

    print("[2/3] Loading Pyannote...")
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=".*torchcodec.*", category=UserWarning
        )
        from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", token=settings.hf_token
    )
    assert pipeline is not None
    pipeline.to(torch.device(settings.pyannote_device))

    print("[3/3] Scanning dataset...")

    # Discover samples
    samples = []
    for category in CATEGORIES:
        cat_dir = os.path.join(DATASET_ROOT, category)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            sample_dir = os.path.join(cat_dir, name)
            if os.path.isdir(sample_dir) and os.path.isfile(
                os.path.join(sample_dir, "ground_truth.json")
            ):
                samples.append(sample_dir)

    print(f"  Found {len(samples)} samples across {len(CATEGORIES)} categories")

    if not samples:
        print("  ERROR: No valid samples found.")
        sys.exit(1)

    # Run all samples
    all_results = []
    all_failures = []
    t_total = time.monotonic()

    for i, sample_dir in enumerate(samples):
        sample_name = os.path.basename(sample_dir)
        category = os.path.basename(os.path.dirname(sample_dir))
        print(f"\n  [{i + 1}/{len(samples)}] {category}/{sample_name}")

        try:
            result = run_sample(pipeline, transcriber, sample_dir, AUDIO_DIR)
            all_results.append(result)

            if "failures" in result:
                for f in result["failures"]:
                    f["audio_file"] = result["recording"]
                    f["sample_name"] = result["sample"]
                all_failures.extend(result["failures"])

            if "error" in result:
                print(f"    ERROR: {result['error']}")
            else:
                f1 = result.get("macro_f1", 0)
                scdr = result.get("scdr", 0)
                acc = result.get("accuracy", 0)
                spk = result.get("speakers_detected", "?")
                status = (
                    "PASS"
                    if f1 >= THRESHOLD_F1
                    and acc / 100 >= THRESHOLD_ACCURACY
                    and scdr / 100 >= THRESHOLD_SCDR
                    else "FAIL"
                )
                print(
                    f"    F1={f1:.3f}  SCDR={scdr:.0f}%  Acc={acc:.0f}%  Spk={spk}  [{status}]"  # noqa: E501
                )

        except Exception as e:
            print(f"    EXCEPTION: {e}")
            all_results.append({"sample": sample_name, "error": str(e)})

    total_time = time.monotonic() - t_total
    valid = [r for r in all_results if "error" not in r]

    # Integrity Check: Did we evaluate all expected samples?
    if len(valid) != len(samples):
        print(
            f"\n  [INTEGRITY FAILURE] Only {len(valid)} / {len(samples)} samples completed successfully."
        )
        print("  Failing the benchmark loudly.")
        sys.exit(1)

    # Aggregate
    if valid:
        avg_f1 = sum(r["macro_f1"] for r in valid) / len(valid)
        avg_acc = sum(r["accuracy"] for r in valid) / len(valid)
        avg_scdr = sum(r["scdr"] for r in valid) / len(valid)

        all_scdr_errors = []
        for r in valid:
            all_scdr_errors.extend(r.get("scdr_errors_ms", []))

        all_scdr_errors.sort()
        avg_boundary_err = (
            sum(all_scdr_errors) / len(all_scdr_errors) if all_scdr_errors else 0.0
        )
        median_boundary_err = (
            all_scdr_errors[len(all_scdr_errors) // 2] if all_scdr_errors else 0.0
        )
        p90_boundary_err = (
            all_scdr_errors[int(len(all_scdr_errors) * 0.9)] if all_scdr_errors else 0.0
        )

        # Percentiles
        within_100 = (
            sum(1 for e in all_scdr_errors if e <= 100.0) / len(all_scdr_errors) * 100
            if all_scdr_errors
            else 0.0
        )
        within_250 = (
            sum(1 for e in all_scdr_errors if e <= 250.0) / len(all_scdr_errors) * 100
            if all_scdr_errors
            else 0.0
        )
        within_500 = (
            sum(1 for e in all_scdr_errors if e <= 500.0) / len(all_scdr_errors) * 100
            if all_scdr_errors
            else 0.0
        )
        within_750 = (
            sum(1 for e in all_scdr_errors if e <= 750.0) / len(all_scdr_errors) * 100
            if all_scdr_errors
            else 0.0
        )
        within_1000 = (
            sum(1 for e in all_scdr_errors if e <= 1000.0) / len(all_scdr_errors) * 100
            if all_scdr_errors
            else 0.0
        )

        # Detailed SCDR Metrics
        total_gt_transitions = sum(
            r.get("scdr_detailed", {}).get("gt_count", 0) for r in valid
        )
        total_pred_transitions = sum(
            r.get("scdr_detailed", {}).get("pred_count", 0) for r in valid
        )
        total_tp = sum(r.get("scdr_detailed", {}).get("tp", 0) for r in valid)
        total_fn = sum(r.get("scdr_detailed", {}).get("fn", 0) for r in valid)
        total_fp = sum(r.get("scdr_detailed", {}).get("fp", 0) for r in valid)
        total_wrong_spk = sum(
            r.get("scdr_detailed", {}).get("wrong_spk", 0) for r in valid
        )

        overall_prec = (
            (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
        )
        overall_rec = (
            (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0
        )
        overall_f1 = (
            (2 * overall_prec * overall_rec) / (overall_prec + overall_rec)
            if (overall_prec + overall_rec) > 0
            else 0.0
        )

    else:
        avg_f1 = avg_acc = avg_scdr = avg_boundary_err = median_boundary_err = (
            p90_boundary_err
        ) = 0.0
        within_100 = within_250 = within_500 = within_750 = within_1000 = 0.0
        total_gt_transitions = total_pred_transitions = total_tp = total_fn = (
            total_fp
        ) = total_wrong_spk = 0
        overall_prec = overall_rec = overall_f1 = 0.0

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_samples": len(all_results),
        "valid_samples": len(valid),
        "errored_samples": len(all_results) - len(valid),
        "total_time_s": round(total_time, 1),
        "aggregate": {
            "avg_macro_f1": round(avg_f1, 4),
            "avg_accuracy": round(avg_acc, 1),
            "avg_scdr": round(avg_scdr, 1),
            "boundary_error_avg_ms": round(avg_boundary_err, 1),
            "boundary_error_median_ms": round(median_boundary_err, 1),
            "boundary_error_p90_ms": round(p90_boundary_err, 1),
            "within_100ms": round(within_100, 1),
            "within_250ms": round(within_250, 1),
            "within_500ms": round(within_500, 1),
            "within_750ms": round(within_750, 1),
            "within_1000ms": round(within_1000, 1),
            "total_gt_transitions": total_gt_transitions,
            "total_pred_transitions": total_pred_transitions,
            "total_tp": total_tp,
            "total_fn": total_fn,
            "total_fp": total_fp,
            "total_wrong_spk": total_wrong_spk,
            "scdr_precision": round(overall_prec, 4),
            "scdr_recall": round(overall_rec, 4),
            "scdr_f1": round(overall_f1, 4),
            "f1_pass": avg_f1 >= THRESHOLD_F1,
            "accuracy_pass": avg_acc / 100 >= THRESHOLD_ACCURACY if valid else False,
            "scdr_pass": avg_scdr / 100 >= THRESHOLD_SCDR if valid else False,
            "production_ready": (
                (
                    avg_f1 >= THRESHOLD_F1
                    and avg_acc / 100 >= THRESHOLD_ACCURACY
                    and avg_scdr / 100 >= THRESHOLD_SCDR
                )
                if valid
                else False
            ),
        },
        "per_sample": all_results,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    with open(ERROR_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(all_failures, f, indent=2, default=str)

    # Generate markdown report
    report_path = generate_report(all_results, OUTPUT_PATH)

    # Print summary
    print(f"\n{'=' * 70}")
    print("  BENCHMARK COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Samples:     {len(valid)} valid / {len(all_results)} total")
    print(f"  Total time:  {total_time:.1f}s")
    print(f"  Avg F1:      {avg_f1:.4f} (threshold: {THRESHOLD_F1})")
    print(f"  Avg Accuracy:{avg_acc:.1f}% (threshold: {THRESHOLD_ACCURACY * 100}%)")
    print(f"  Avg SCDR:    {avg_scdr:.1f}% (threshold: {THRESHOLD_SCDR * 100}%)")

    all_pass = (
        avg_f1 >= THRESHOLD_F1
        and avg_acc / 100 >= THRESHOLD_ACCURACY
        and avg_scdr / 100 >= THRESHOLD_SCDR
    )
    print(
        f"\n  VERDICT: {'[PRODUCTION READY]' if all_pass else '[NOT PRODUCTION READY]'}"
    )
    print(f"\n  Results: {OUTPUT_PATH}")
    print(f"  Report:  {report_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
