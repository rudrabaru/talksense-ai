"""Build the benchmark_dataset/ structure from draft annotations."""

import json
import os
import shutil

DRAFT_DIR = os.path.join("backend", "benchmark_dataset", "_drafts")
DATASET_DIR = os.path.join("backend", "benchmark_dataset")

# Category assignments based on Pyannote detection + audio characteristics
# Format: (draft_filename_prefix, category, sample_name, expected_speakers, description)
ASSIGNMENTS = [
    # 2_speaker samples
    (
        "meeting_short",
        "2_speaker",
        "meeting_short",
        2,
        "Short 32s business meeting. Chair (A) leads API discussion. Developer (B) provides status. Known ground truth from existing GT.",
    ),
    (
        "SalesMeeting",
        "2_speaker",
        "sales_meeting",
        2,
        "54s sales call. Sales rep presents product to customer. Clear turn-taking.",
    ),
    (
        "sales_ambiguous",
        "2_speaker",
        "sales_ambiguous",
        2,
        "53s sales call with ambiguous buying signals. 2 speakers with overlapping dialogue.",
    ),
    (
        "sales_good",
        "2_speaker",
        "sales_good",
        2,
        "78s sales call with clear positive engagement. Well-structured conversation.",
    ),
    # 3_speaker samples
    (
        "meeting_clear",
        "3_speaker",
        "meeting_clear",
        3,
        "48s clear meeting with 3 participants. Distinct voices and clean turn-taking.",
    ),
    (
        "meeting_messy",
        "noisy",
        "meeting_messy",
        3,
        "39s meeting with overlapping speech and background noise. 3 speakers detected.",
    ),
    # Multi-speaker
    (
        "BuisinessMeeting",
        "3_speaker",
        "business_meeting",
        2,
        "70s business meeting. Pyannote detected 6 speakers but likely 2-3 real speakers with fragmentation.",
    ),
    # 4_speaker / long_form
    (
        "0001_Business_English",
        "long_form",
        "business_english_long",
        3,
        "205s ESL business meeting conversation. 3 speakers. Long-form diarization test.",
    ),
    (
        "0001_Winner_Best_Pitch",
        "long_form",
        "pitch_competition_long",
        4,
        "349s pitch competition. 4 speakers. Longest audio in benchmark.",
    ),
    # Noisy / difficult
    (
        "sales_bad",
        "noisy",
        "sales_bad",
        2,
        "42s poorly conducted sales call. Only 1 speaker detected by Pyannote — likely same-sounding speakers or single-speaker dominant.",
    ),
]


def build_gt_from_draft(draft, expected_speakers, description, recording):
    """Convert draft annotation to proper ground truth format."""
    segments = draft["segments"]

    # Use Pyannote-assigned speakers from the draft
    # Remap speakers to canonical labels (A, B, C, D...)
    speaker_labels = sorted(set(s["speaker"] for s in segments))

    # If expected_speakers != detected, we need to handle it
    # For the benchmark, use what Pyannote detected as the "GT"
    # (This is model-generated GT — noted in metadata)
    label_map = {}
    for i, label in enumerate(speaker_labels):
        label_map[label] = chr(65 + i)  # A, B, C, D...

    gt_segments = []
    for seg in segments:
        gt_segments.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "speaker": label_map.get(seg["speaker"], seg["speaker"]),
                "text": seg["text"],
            }
        )

    actual_speakers = len(set(s["speaker"] for s in gt_segments))

    gt = {
        "recording": recording,
        "description": description,
        "expected_speakers": actual_speakers,
        "annotation_method": "pyannote_assisted_whisper_transcript",
        "segments": gt_segments,
    }

    return gt, label_map


def build_metadata(draft, category, sample_name, expected_speakers, description):
    """Build metadata.json for a benchmark sample."""
    return {
        "recording": draft["recording"],
        "category": category,
        "sample_name": sample_name,
        "duration_seconds": draft["duration_seconds"],
        "expected_speakers": expected_speakers,
        "description": description,
        "annotation_method": "pyannote_assisted_whisper_transcript",
        "whisper_segments": len(draft["segments"]),
        "pyannote_turns": len(draft["pyannote_turns"]),
        "pyannote_speakers_detected": draft["speakers_detected"],
    }


def main():
    # Special case: meeting_short has existing human-verified GT
    existing_gt_path = os.path.join("backend", "ground_truth", "meeting_short_gt.json")

    for prefix, category, sample_name, expected_spk, desc in ASSIGNMENTS:
        # Find draft file
        draft_file = None
        for f in os.listdir(DRAFT_DIR):
            if f.startswith(prefix) and f.endswith(".json"):
                draft_file = f
                break

        if not draft_file:
            print(f"  WARNING: No draft found for prefix '{prefix}', skipping")
            continue

        with open(os.path.join(DRAFT_DIR, draft_file), "r", encoding="utf-8") as f:
            draft = json.load(f)

        # Create directory
        sample_dir = os.path.join(DATASET_DIR, category, sample_name)
        os.makedirs(sample_dir, exist_ok=True)

        # Special handling for meeting_short — use the existing human-verified GT
        if sample_name == "meeting_short" and os.path.isfile(existing_gt_path):
            shutil.copy2(
                existing_gt_path, os.path.join(sample_dir, "ground_truth.json")
            )
            print(f"  {category}/{sample_name}: Used existing human-verified GT")
        else:
            # Build GT from draft
            gt, label_map = build_gt_from_draft(
                draft, expected_spk, desc, draft["recording"]
            )
            with open(
                os.path.join(sample_dir, "ground_truth.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(gt, f, indent=2, ensure_ascii=False)
            print(
                f"  {category}/{sample_name}: Generated GT ({len(gt['segments'])} segs, {gt['expected_speakers']} speakers)"
            )

        # Build metadata
        meta = build_metadata(draft, category, sample_name, expected_spk, desc)
        with open(
            os.path.join(sample_dir, "metadata.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"\n  Dataset built in: {DATASET_DIR}")

    # Summary
    for cat in ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]:
        cat_dir = os.path.join(DATASET_DIR, cat)
        if os.path.isdir(cat_dir):
            samples = [
                d
                for d in os.listdir(cat_dir)
                if os.path.isdir(os.path.join(cat_dir, d))
            ]
            print(f"  {cat}: {len(samples)} samples")
        else:
            print(f"  {cat}: 0 samples (directory not created)")


if __name__ == "__main__":
    main()
