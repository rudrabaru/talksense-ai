import json
import os


def load_ground_truth(sample_name):
    # Depending on where the script is run, try to find ground_truth.json
    categories = ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]
    for cat in categories:
        gt_path = os.path.join(
            "benchmark_dataset", cat, sample_name, "ground_truth.json"
        )
        if os.path.exists(gt_path):
            with open(gt_path, "r") as f:
                return json.load(f).get("segments", [])
    return []


def main():
    if not os.path.exists("scdr_error_log.json"):
        print("No error log found.")
        return

    with open("scdr_error_log.json", "r") as f:
        failures = json.load(f)

    # Categories
    counts = {
        "Whisper Segmentation": 0,
        "Pyannote Clustering": 0,
        "Overlapping Speech": 0,
        "Unknown": 0,
    }

    # Cache ground truths
    gts = {}
    for f in failures:
        sn = f.get("sample_name")
        if sn and sn not in gts:
            gts[sn] = load_ground_truth(sn)

    classified = []

    for f in failures:
        sn = f.get("sample_name")
        start = f["start"]
        end = f["end"]

        # Check ground truth for overlap or segmentation issues in this timeframe
        gt_segments = gts.get(sn, [])
        overlapping_gt_speakers = set()

        for gt in gt_segments:
            gt_start = gt["start"]
            gt_end = gt["end"]
            # Check overlap
            overlap = max(0, min(end, gt_end) - max(start, gt_start))
            if overlap > 0:
                overlapping_gt_speakers.add(gt["speaker"])

        num_gt_speakers = len(overlapping_gt_speakers)

        category = "Unknown"
        if num_gt_speakers > 1:
            category = "Whisper Segmentation"
            counts["Whisper Segmentation"] += 1
        elif num_gt_speakers == 1:
            category = "Pyannote Clustering"
            counts["Pyannote Clustering"] += 1
        else:
            category = "Unknown"
            counts["Unknown"] += 1

        f["category"] = category
        f["overlapping_gt_speakers"] = list(overlapping_gt_speakers)
        classified.append(f)

    with open("scdr_error_log_classified.json", "w") as out:
        json.dump(classified, out, indent=2)

    total = len(failures)
    print("\n--- Error Classification ---")
    print(f"Total Errors: {total}")
    for k, v in counts.items():
        pct = (v / total * 100) if total > 0 else 0
        print(f"{k}: {v} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
