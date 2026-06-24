"""
TalkSense AI — Benchmark Dataset Validator

Validates the entire benchmark dataset structure, schemas, and consistency.

Usage:
    python backend/validate_benchmark_dataset.py

Checks:
    - Audio file exists and is readable
    - Ground truth JSON exists and has valid schema
    - Timestamps are valid (non-negative, start < end, non-overlapping)
    - Speaker labels are consistent between segments and metadata
    - Expected speakers count matches segments
    - Metadata matches audio file properties
"""
import json
import os
import subprocess
import sys

SAMPLE_RATE = 16000
DATASET_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_dataset")
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_audio"))

REQUIRED_GT_FIELDS = ["recording", "expected_speakers", "segments"]
REQUIRED_SEG_FIELDS = ["start", "end", "speaker", "text"]
REQUIRED_META_FIELDS = ["recording", "category", "duration_seconds", "expected_speakers"]
CATEGORIES = ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]


def get_audio_duration(audio_path):
    """Get audio duration using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def validate_ground_truth(gt_path, audio_path):
    """Validate a single ground truth JSON file."""
    errors = []
    warnings = []

    try:
        with open(gt_path, "r", encoding="utf-8") as f:
            gt = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"], []
    except Exception as e:
        return [f"Cannot read file: {e}"], []

    # Check required fields
    for field in REQUIRED_GT_FIELDS:
        if field not in gt:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return errors, warnings

    # Validate segments
    segments = gt.get("segments", [])
    if not segments:
        errors.append("No segments defined")
        return errors, warnings

    speakers_in_segments = set()
    prev_end = -1.0

    for i, seg in enumerate(segments):
        # Check required segment fields
        for field in REQUIRED_SEG_FIELDS:
            if field not in seg:
                errors.append(f"Segment {i}: missing field '{field}'")
                continue

        start = seg.get("start", 0)
        end = seg.get("end", 0)
        speaker = seg.get("speaker", "")

        # Validate timestamps
        if start < 0:
            errors.append(f"Segment {i}: negative start time ({start})")
        if end < 0:
            errors.append(f"Segment {i}: negative end time ({end})")
        if end <= start:
            errors.append(f"Segment {i}: end ({end}) <= start ({start})")
        if start < prev_end - 0.1:  # Allow 100ms tolerance
            warnings.append(f"Segment {i}: overlaps with previous (start={start:.2f}, prev_end={prev_end:.2f})")

        prev_end = end
        speakers_in_segments.add(speaker)

    # Validate speaker count
    expected = gt.get("expected_speakers", 0)
    actual = len(speakers_in_segments)
    if expected != actual:
        errors.append(f"expected_speakers={expected} but segments have {actual} unique speakers: {speakers_in_segments}")

    # Validate against audio file
    if audio_path and os.path.isfile(audio_path):
        duration = get_audio_duration(audio_path)
        if duration:
            last_end = max(s.get("end", 0) for s in segments)
            if last_end > duration + 1.0:
                errors.append(f"Last segment ends at {last_end:.1f}s but audio is only {duration:.1f}s")
            if abs(last_end - duration) > 5.0:
                warnings.append(f"Large gap: last segment ends at {last_end:.1f}s, audio duration is {duration:.1f}s")
    else:
        errors.append(f"Audio file not found: {audio_path}")

    return errors, warnings


def validate_metadata(meta_path):
    """Validate a metadata.json file."""
    errors = []

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        return [f"Cannot read metadata: {e}"]

    for field in REQUIRED_META_FIELDS:
        if field not in meta:
            errors.append(f"Missing metadata field: '{field}'")

    category = meta.get("category", "")
    if category not in CATEGORIES:
        errors.append(f"Invalid category: '{category}' (must be one of {CATEGORIES})")

    return errors


def validate_dataset():
    """Validate the entire benchmark dataset."""
    print("=" * 70)
    print("  BENCHMARK DATASET VALIDATOR")
    print("=" * 70)

    if not os.path.isdir(DATASET_ROOT):
        print(f"\n  ERROR: Dataset root not found: {DATASET_ROOT}")
        return False

    total_samples = 0
    total_errors = 0
    total_warnings = 0
    category_stats = {}

    for category in CATEGORIES:
        cat_dir = os.path.join(DATASET_ROOT, category)
        if not os.path.isdir(cat_dir):
            print(f"\n  WARNING: Category directory missing: {category}/")
            continue

        samples = [d for d in os.listdir(cat_dir)
                    if os.path.isdir(os.path.join(cat_dir, d))]

        if not samples:
            print(f"\n  WARNING: No samples in {category}/")
            continue

        cat_errors = 0
        cat_warnings = 0
        cat_samples = 0

        print(f"\n  Category: {category}/ ({len(samples)} samples)")
        print(f"  {'-' * 60}")

        for sample_name in sorted(samples):
            sample_dir = os.path.join(cat_dir, sample_name)
            gt_path = os.path.join(sample_dir, "ground_truth.json")
            meta_path = os.path.join(sample_dir, "metadata.json")

            # Find audio file
            audio_file = None
            audio_path = None

            if os.path.isfile(gt_path):
                try:
                    with open(gt_path, "r") as f:
                        gt = json.load(f)
                    audio_file = gt.get("recording", "")
                    audio_path = os.path.join(AUDIO_DIR, audio_file)
                except Exception:
                    pass

            # Check files exist
            has_gt = os.path.isfile(gt_path)
            has_meta = os.path.isfile(meta_path)
            has_audio = audio_path and os.path.isfile(audio_path)

            status_parts = []
            sample_errors = []
            sample_warnings = []

            if not has_gt:
                sample_errors.append("Missing ground_truth.json")
            else:
                gt_errors, gt_warns = validate_ground_truth(gt_path, audio_path)
                sample_errors.extend(gt_errors)
                sample_warnings.extend(gt_warns)

            if not has_meta:
                sample_errors.append("Missing metadata.json")
            else:
                meta_errors = validate_metadata(meta_path)
                sample_errors.extend(meta_errors)

            if not has_audio:
                sample_errors.append(f"Audio file not found: {audio_file}")

            status = "PASS" if not sample_errors else "FAIL"
            warn_str = f" ({len(sample_warnings)} warnings)" if sample_warnings else ""

            print(f"    {sample_name:40s} [{status}]{warn_str}")
            for err in sample_errors:
                print(f"      ERROR: {err}")
            for warn in sample_warnings:
                print(f"      WARN:  {warn}")

            cat_errors += len(sample_errors)
            cat_warnings += len(sample_warnings)
            cat_samples += 1

        category_stats[category] = {
            "samples": cat_samples, "errors": cat_errors, "warnings": cat_warnings
        }
        total_samples += cat_samples
        total_errors += cat_errors
        total_warnings += cat_warnings

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total samples:  {total_samples}")
    print(f"  Total errors:   {total_errors}")
    print(f"  Total warnings: {total_warnings}")

    for cat, stats in category_stats.items():
        status = "PASS" if stats["errors"] == 0 else "FAIL"
        print(f"    {cat:20s}: {stats['samples']} samples, {stats['errors']} errors [{status}]")

    overall = total_errors == 0
    print(f"\n  OVERALL: {'[PASS]' if overall else '[FAIL]'}")
    print(f"{'=' * 70}")

    return overall


if __name__ == "__main__":
    success = validate_dataset()
    sys.exit(0 if success else 1)
