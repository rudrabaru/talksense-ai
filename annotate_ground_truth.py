"""
TalkSense AI — Ground Truth Annotation Tool

Interactive CLI tool for reviewing and correcting speaker labels in
benchmark ground truth files.

Usage:
    python annotate_ground_truth.py <sample_path>
    python annotate_ground_truth.py backend/benchmark_dataset/2_speaker/sales_meeting

Features:
    - Loads audio metadata + existing GT
    - Shows each segment with text + current speaker label
    - Allows editing individual segment speaker labels
    - Allows batch reassignment of speakers
    - Saves revised GT with annotation_method = "human_reviewed"
    - Preserves original GT as ground_truth_original.json backup
"""
import json
import os
import shutil
import sys
import subprocess
from datetime import datetime


SAMPLE_RATE = 16000
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_audio"))


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


def load_sample(sample_dir):
    """Load ground truth and metadata for a sample."""
    gt_path = os.path.join(sample_dir, "ground_truth.json")
    meta_path = os.path.join(sample_dir, "metadata.json")

    if not os.path.isfile(gt_path):
        print(f"ERROR: ground_truth.json not found in {sample_dir}")
        sys.exit(1)

    with open(gt_path, "r", encoding="utf-8") as f:
        gt = json.load(f)

    meta = None
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    return gt, meta


def display_segments(segments, highlight_idx=None):
    """Display all segments with speaker labels and text."""
    speakers = sorted(set(s["speaker"] for s in segments))
    print(f"\n  Speakers: {speakers}")
    print(f"  Total segments: {len(segments)}")
    print(f"  {'─' * 80}")

    for i, seg in enumerate(segments):
        marker = ">>>" if i == highlight_idx else "   "
        text = seg["text"][:65]
        print(f"  {marker} [{i:3d}] {seg['start']:7.2f} - {seg['end']:7.2f}  {seg['speaker']:4s}  │ {text}")

    print(f"  {'─' * 80}")


def display_speaker_summary(segments):
    """Show per-speaker segment count and total duration."""
    stats = {}
    for seg in segments:
        spk = seg["speaker"]
        dur = seg["end"] - seg["start"]
        if spk not in stats:
            stats[spk] = {"count": 0, "duration": 0.0, "first_text": seg["text"][:40]}
        stats[spk]["count"] += 1
        stats[spk]["duration"] += dur

    print(f"\n  Speaker Summary:")
    print(f"  {'Speaker':<8} {'Segments':>8} {'Duration':>10} {'First utterance'}")
    print(f"  {'─' * 70}")
    for spk in sorted(stats.keys()):
        s = stats[spk]
        print(f"  {spk:<8} {s['count']:>8} {s['duration']:>9.1f}s  {s['first_text']}")
    print()


def display_transitions(segments):
    """Show speaker transitions to help identify misattributions."""
    print(f"\n  Speaker Transitions:")
    prev_speaker = None
    for i, seg in enumerate(segments):
        if seg["speaker"] != prev_speaker:
            if prev_speaker is not None:
                print(f"    [{i:3d}] {prev_speaker} → {seg['speaker']}  at {seg['start']:.2f}s  │ {seg['text'][:50]}")
            prev_speaker = seg["speaker"]
    print()


def edit_segment(segments, idx, new_speaker):
    """Change the speaker label of a single segment."""
    if 0 <= idx < len(segments):
        old = segments[idx]["speaker"]
        segments[idx]["speaker"] = new_speaker
        return old
    return None


def batch_reassign(segments, old_speaker, new_speaker):
    """Reassign all segments from old_speaker to new_speaker."""
    count = 0
    for seg in segments:
        if seg["speaker"] == old_speaker:
            seg["speaker"] = new_speaker
            count += 1
    return count


def interactive_review(sample_dir):
    """Interactive annotation session."""
    gt, meta = load_sample(sample_dir)
    segments = gt.get("segments", [])
    recording = gt.get("recording", "unknown")

    sample_name = os.path.basename(sample_dir)
    category = os.path.basename(os.path.dirname(sample_dir))

    # Get audio info
    audio_path = os.path.join(AUDIO_DIR, recording)
    duration = get_audio_duration(audio_path) if os.path.isfile(audio_path) else None

    print("=" * 80)
    print(f"  GROUND TRUTH ANNOTATION TOOL")
    print("=" * 80)
    print(f"  Sample:     {category}/{sample_name}")
    print(f"  Recording:  {recording}")
    print(f"  Duration:   {duration:.1f}s" if duration else "  Duration:   unknown")
    print(f"  GT Method:  {gt.get('annotation_method', 'unknown')}")
    print(f"  Expected:   {gt.get('expected_speakers', '?')} speakers")
    print(f"  Description: {gt.get('description', 'none')}")

    display_segments(segments)
    display_speaker_summary(segments)
    display_transitions(segments)

    modified = False

    while True:
        print("\n  Commands:")
        print("    e <idx> <speaker>    — Edit segment <idx> to <speaker> (e.g. 'e 3 B')")
        print("    b <old> <new>        — Batch reassign all <old> → <new> (e.g. 'b A B')")
        print("    r <idx_range> <spk>  — Range edit (e.g. 'r 5-8 B')")
        print("    v                    — View all segments")
        print("    t                    — View transitions")
        print("    s                    — View speaker summary")
        print("    n <count>            — Set expected_speakers count")
        print("    d <text>             — Update description")
        print("    w                    — Save and exit")
        print("    q                    — Quit without saving")

        try:
            cmd = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=2)
        action = parts[0].lower()

        if action == "q":
            if modified:
                confirm = input("  Unsaved changes. Quit anyway? (y/n) > ").strip().lower()
                if confirm != "y":
                    continue
            print("  Exiting without saving.")
            return

        elif action == "w":
            # Save
            save_revised_gt(sample_dir, gt, segments)
            print("  Saved successfully.")
            return

        elif action == "v":
            display_segments(segments)

        elif action == "t":
            display_transitions(segments)

        elif action == "s":
            display_speaker_summary(segments)

        elif action == "e" and len(parts) >= 3:
            try:
                idx = int(parts[1])
                new_spk = parts[2].upper()
                old = edit_segment(segments, idx, new_spk)
                if old:
                    print(f"  Segment {idx}: {old} → {new_spk}")
                    modified = True
                else:
                    print(f"  Invalid index: {idx}")
            except ValueError:
                print("  Usage: e <index> <speaker>")

        elif action == "b" and len(parts) >= 3:
            old_spk = parts[1].upper()
            new_spk = parts[2].upper()
            count = batch_reassign(segments, old_spk, new_spk)
            print(f"  Reassigned {count} segments: {old_spk} → {new_spk}")
            if count > 0:
                modified = True

        elif action == "r" and len(parts) >= 3:
            try:
                range_str = parts[1]
                new_spk = parts[2].upper()
                if "-" in range_str:
                    start, end = range_str.split("-")
                    for idx in range(int(start), int(end) + 1):
                        old = edit_segment(segments, idx, new_spk)
                        if old and old != new_spk:
                            print(f"  Segment {idx}: {old} → {new_spk}")
                    modified = True
                else:
                    print("  Usage: r <start>-<end> <speaker>")
            except (ValueError, IndexError):
                print("  Usage: r <start>-<end> <speaker>")

        elif action == "n" and len(parts) >= 2:
            try:
                gt["expected_speakers"] = int(parts[1])
                print(f"  Expected speakers set to {parts[1]}")
                modified = True
            except ValueError:
                print("  Usage: n <count>")

        elif action == "d" and len(parts) >= 2:
            gt["description"] = " ".join(parts[1:])
            print(f"  Description updated.")
            modified = True

        else:
            print("  Unknown command. Try 'v', 'e', 'b', 'r', 'w', or 'q'.")


def save_revised_gt(sample_dir, gt, segments):
    """Save revised GT with backup of original."""
    gt_path = os.path.join(sample_dir, "ground_truth.json")
    backup_path = os.path.join(sample_dir, "ground_truth_original.json")

    # Backup original if not already backed up
    if not os.path.isfile(backup_path):
        shutil.copy2(gt_path, backup_path)
        print(f"  Original backed up to: ground_truth_original.json")

    # Update GT
    gt["segments"] = segments
    gt["annotation_method"] = "human_reviewed"
    gt["review_date"] = datetime.now().strftime("%Y-%m-%d")
    gt["expected_speakers"] = len(set(s["speaker"] for s in segments))

    # Update metadata too
    meta_path = os.path.join(sample_dir, "metadata.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["annotation_method"] = "human_reviewed"
        meta["review_date"] = gt["review_date"]
        meta["expected_speakers"] = gt["expected_speakers"]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2, ensure_ascii=False)


def batch_review_all():
    """Show summary of all samples for batch review prioritization."""
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "benchmark_dataset")

    print("=" * 80)
    print("  BENCHMARK DATASET — ANNOTATION STATUS")
    print("=" * 80)

    categories = ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]
    for cat in categories:
        cat_dir = os.path.join(dataset_dir, cat)
        if not os.path.isdir(cat_dir):
            continue

        print(f"\n  {cat}/")
        for name in sorted(os.listdir(cat_dir)):
            sample_dir = os.path.join(cat_dir, name)
            if not os.path.isdir(sample_dir):
                continue

            gt_path = os.path.join(sample_dir, "ground_truth.json")
            if not os.path.isfile(gt_path):
                continue

            with open(gt_path, "r", encoding="utf-8") as f:
                gt = json.load(f)

            method = gt.get("annotation_method", "unknown")
            speakers = len(set(s["speaker"] for s in gt.get("segments", [])))
            segs = len(gt.get("segments", []))

            status = "✓ REVIEWED" if method == "human_reviewed" else "⚠ UNREVIEWED"
            print(f"    {name:35s} {segs:3d} segs  {speakers} spk  [{status}]")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python annotate_ground_truth.py <sample_dir>      — Review a single sample")
        print("  python annotate_ground_truth.py --status           — Show annotation status")
        print()
        print("Example:")
        print("  python annotate_ground_truth.py backend/benchmark_dataset/2_speaker/sales_meeting")
        batch_review_all()
        return

    if sys.argv[1] == "--status":
        batch_review_all()
        return

    sample_dir = sys.argv[1]
    if not os.path.isdir(sample_dir):
        # Try relative to project root
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), sample_dir)
        if os.path.isdir(alt):
            sample_dir = alt
        else:
            print(f"ERROR: Directory not found: {sample_dir}")
            sys.exit(1)

    interactive_review(sample_dir)


if __name__ == "__main__":
    main()
