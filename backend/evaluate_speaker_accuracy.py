"""
TalkSense AI — Ground-Truth Speaker Attribution Accuracy Evaluator

Computes true attribution accuracy by comparing Pyannote-assigned speaker labels
in transcript_segments against manually annotated ground-truth speaker labels.

Metrics computed:
  - Attribution Accuracy (after label permutation mapping)
  - Per-speaker Precision, Recall, F1
  - Macro-F1 across all speakers
  - Speaker Change Detection Rate (SCDR)
  - Coverage (from session_metrics)

Usage:
    python -m backend.evaluate_speaker_accuracy \\
        --session-id <uuid> \\
        --ground-truth backend/ground_truth/meeting_short_gt.json \\
        --output speaker_attribution_accuracy_report.md

Ground truth JSON format:
    {
      "recording": "meeting_short.mp3",
      "expected_speakers": 3,
      "segments": [
        { "start": 0.0, "end": 3.5, "speaker": "A", "text": "..." },
        ...
      ]
    }

Design:
  - Read-only: does NOT modify any DB rows or pipeline code.
  - Segment matching: maximum-overlap alignment with 50% minimum threshold.
  - Label mapping: greedy majority-vote permutation to align Pyannote labels
    (e.g. "Speaker 3") to canonical annotator labels (e.g. "A").
"""

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from db import crud
from db.database import AsyncSessionLocal

# ── Data types ────────────────────────────────────────────────────────────────


class Segment:
    """Unified segment representation for both predicted and annotated data."""

    def __init__(self, start: float, end: float, speaker: str, text: str = ""):
        self.start = start
        self.end = end
        self.speaker = speaker
        self.text = text

    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def overlap(self, other: "Segment") -> float:
        return max(0.0, min(self.end, other.end) - max(self.start, other.start))

    def __repr__(self) -> str:
        return f"Segment({self.start:.2f}-{self.end:.2f}, {self.speaker!r})"


# ── Ground truth loading ───────────────────────────────────────────────────────


def load_ground_truth(path: str) -> Tuple[List[Segment], Dict]:
    """Parse the ground truth annotation JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = []
    for raw in data.get("segments", []):
        segments.append(
            Segment(
                start=float(raw["start"]),
                end=float(raw["end"]),
                speaker=str(raw["speaker"]),
                text=raw.get("text", ""),
            )
        )

    # Sort by start time
    segments.sort(key=lambda s: s.start)
    metadata = {
        "recording": data.get("recording", "unknown"),
        "expected_speakers": data.get("expected_speakers", 0),
    }
    return segments, metadata


# ── DB fetching ───────────────────────────────────────────────────────────────


async def fetch_predicted_segments(session_id: str) -> List[Segment]:
    """Fetch all transcript segments from DB for a session."""
    async with AsyncSessionLocal() as db:
        rows = await crud.get_all_transcript_segments(db, session_id)
    segments = []
    for r in rows:
        segments.append(
            Segment(
                start=r.start_time,
                end=r.end_time,
                speaker=r.speaker_id or "Unknown",
                text=r.text or "",
            )
        )
    segments.sort(key=lambda s: s.start)
    return segments


async def fetch_coverage(session_id: str) -> Optional[float]:
    """Fetch coverage_percent from session_metrics."""
    async with AsyncSessionLocal() as db:
        metrics = await crud.get_latest_session_metrics(db, session_id)
    for m in metrics:
        if m.metric_name == "speaker_attribution":
            return (m.metric_value or {}).get("coverage_percent")
    return None


# ── Segment matching ──────────────────────────────────────────────────────────


def match_segments(
    predicted: List[Segment],
    annotated: List[Segment],
    min_overlap_ratio: float = 0.10,
) -> List[Tuple[Segment, Segment]]:
    """
    Align each predicted segment to the annotated segment with the greatest overlap.

    The ground truth annotations are coarse (one per Whisper output segment, 2-6s),
    while predicted segments from the DB are fine-grained (~1s each). This is a
    many-to-one mapping: multiple predicted segments may match the same annotated
    segment (and that is correct — they all inherit the annotated speaker label).

    A predicted segment is included in the result if the overlap with its best
    annotated match covers at least min_overlap_ratio of the predicted segment's
    own duration.

    Returns list of (predicted, annotated) pairs (one entry per predicted segment).
    """
    pairs = []

    for pred in predicted:
        best_ann = None
        best_overlap = 0.0

        for ann in annotated:
            ov = pred.overlap(ann)
            if ov > best_overlap:
                best_overlap = ov
                best_ann = ann

        pred_dur = pred.duration()
        if best_ann and pred_dur > 0 and (best_overlap / pred_dur) >= min_overlap_ratio:
            pairs.append((pred, best_ann))

    return pairs


# ── Label permutation mapping ─────────────────────────────────────────────────


def resolve_label_mapping(pairs: List[Tuple[Segment, Segment]]) -> Dict[str, str]:
    """
    Greedy majority-vote permutation to map Pyannote labels → canonical labels.

    Builds a co-occurrence matrix: for each (predicted_label, annotated_label)
    pair, increments a count. Then greedily assigns each predicted label to the
    annotated label it co-occurs with most frequently (each annotated label can
    only be assigned once).

    Returns: { predicted_label: canonical_label }
    """
    # Build co-occurrence counts: cooc[pred][ann] = count
    cooc: Dict[str, Counter] = defaultdict(Counter)
    for pred_seg, ann_seg in pairs:
        cooc[pred_seg.speaker][ann_seg.speaker] += 1

    # Greedy assignment: pick highest co-occurrence remaining
    mapping: Dict[str, str] = {}
    assigned_canonical: set = set()

    pred_labels = sorted(
        cooc.keys(), key=lambda label: sum(cooc[label].values()), reverse=True
    )
    for pred_label in pred_labels:
        best_canonical = None
        best_count = 0
        for canonical, count in cooc[pred_label].most_common():
            if canonical not in assigned_canonical and count > best_count:
                best_count = count
                best_canonical = canonical
        if best_canonical:
            mapping[pred_label] = best_canonical
            assigned_canonical.add(best_canonical)
        else:
            # No available canonical — leave as-is (will count as wrong)
            mapping[pred_label] = f"_unmapped_{pred_label}"

    return mapping


# ── Metrics computation ───────────────────────────────────────────────────────


def compute_accuracy(
    pairs: List[Tuple[Segment, Segment]],
    label_map: Dict[str, str],
) -> Tuple[float, int, int]:
    """
    Compute overall attribution accuracy after label mapping.

    Returns: (accuracy_pct, correct_count, total_count)
    """
    correct = sum(
        1
        for pred_seg, ann_seg in pairs
        if label_map.get(pred_seg.speaker) == ann_seg.speaker
    )
    total = len(pairs)
    acc = (correct / total * 100) if total > 0 else 0.0
    return acc, correct, total


def compute_precision_recall_f1(
    pairs: List[Tuple[Segment, Segment]],
    label_map: Dict[str, str],
) -> Dict[str, Dict[str, float]]:
    """
    Compute per-speaker Precision, Recall, F1 after label mapping.

    Returns: { canonical_speaker: { precision, recall, f1 } }
    """
    # Collect all canonical labels that appear in annotations
    all_canonical = set(ann_seg.speaker for _, ann_seg in pairs)

    tp: Dict[str, int] = defaultdict(int)
    fp: Dict[str, int] = defaultdict(int)
    fn: Dict[str, int] = defaultdict(int)

    for pred_seg, ann_seg in pairs:
        mapped = label_map.get(pred_seg.speaker, f"_unmapped_{pred_seg.speaker}")
        if mapped == ann_seg.speaker:
            tp[ann_seg.speaker] += 1
        else:
            fp[mapped] += 1
            fn[ann_seg.speaker] += 1

    results = {}
    for spk in all_canonical:
        t = tp[spk]
        p_count = t + fp[spk]
        r_count = t + fn[spk]
        precision = (t / p_count) if p_count > 0 else 0.0
        recall = (t / r_count) if r_count > 0 else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        results[spk] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": t,
            "fp": fp[spk],
            "fn": fn[spk],
        }
    return results


def compute_scdr(
    predicted: List[Segment],
    annotated: List[Segment],
    label_map: Dict[str, str],
    tolerance_sec: float = 0.5,
) -> Tuple[float, int, int]:
    """
    Speaker Change Detection Rate.

    Identifies speaker change boundaries in both the annotated and predicted
    timelines. A predicted change is "correct" if a corresponding annotated
    change exists within tolerance_sec.

    Returns: (scdr_pct, correctly_detected, total_annotated_changes)
    """

    def get_changes(segs: List[Segment], use_map: bool = False) -> List[float]:
        """Return timestamps of speaker changes (midpoint between consecutive segs)."""
        changes = []
        for i in range(1, len(segs)):
            prev_spk = segs[i - 1].speaker
            curr_spk = segs[i].speaker
            if use_map:
                prev_spk = label_map.get(prev_spk, prev_spk)
                curr_spk = label_map.get(curr_spk, curr_spk)
            if prev_spk != curr_spk:
                midpoint = (segs[i - 1].end + segs[i].start) / 2
                changes.append(midpoint)
        return changes

    annotated_changes = get_changes(annotated, use_map=False)
    predicted_changes = get_changes(predicted, use_map=True)

    # For each annotated change, check if there's a predicted change within tolerance
    correctly_detected = 0
    used_predicted_changes = set()

    for ann_change in annotated_changes:
        for j, pred_change in enumerate(predicted_changes):
            if (
                j not in used_predicted_changes
                and abs(pred_change - ann_change) <= tolerance_sec
            ):
                correctly_detected += 1
                used_predicted_changes.add(j)
                break

    total = len(annotated_changes)
    scdr = (correctly_detected / total * 100) if total > 0 else 0.0
    return scdr, correctly_detected, total


# ── Failure analysis ──────────────────────────────────────────────────────────


def collect_failures(
    pairs: List[Tuple[Segment, Segment]],
    label_map: Dict[str, str],
    limit: int = 10,
) -> List[Dict]:
    """Return details of misattributed segments."""
    failures = []
    for pred_seg, ann_seg in pairs:
        mapped = label_map.get(pred_seg.speaker, pred_seg.speaker)
        if mapped != ann_seg.speaker:
            failures.append(
                {
                    "start": pred_seg.start,
                    "end": pred_seg.end,
                    "predicted_raw": pred_seg.speaker,
                    "predicted_mapped": mapped,
                    "expected": ann_seg.speaker,
                    "text": pred_seg.text[:60],
                }
            )
    return failures[:limit]


# ── Report generation ─────────────────────────────────────────────────────────


def generate_report(
    session_id: str,
    recording: str,
    coverage: Optional[float],
    accuracy: float,
    correct: int,
    total_matched: int,
    per_speaker: Dict[str, Dict],
    scdr: float,
    scdr_detected: int,
    scdr_total: int,
    label_map: Dict[str, str],
    failures: List[Dict],
    matched_count: int,
    annotated_count: int,
) -> str:
    """Generate the full markdown accuracy report."""
    macro_f1 = (
        (sum(v["f1"] for v in per_speaker.values()) / len(per_speaker))
        if per_speaker
        else 0.0
    )

    # Recommendation thresholds
    is_safe = macro_f1 >= 0.75 and scdr >= 70.0
    recommendation = (
        "**Role Classification Safe**"
        if is_safe
        else "**Role Classification Not Yet Safe**"
    )

    lines = []
    lines.append("# Speaker Attribution Accuracy Report")
    lines.append(f"\nGenerated for session `{session_id}` | Recording: `{recording}`")

    lines.append("\n---\n## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(
        f"| Coverage | {coverage:.1f}% |"
        if coverage is not None
        else "| Coverage | N/A |"
    )
    lines.append(
        f"| Segments Matched | {matched_count} / {annotated_count} annotated |"
    )
    lines.append(
        f"| Attribution Accuracy | {accuracy:.1f}% ({correct}/{total_matched}) |"
    )
    lines.append(f"| Macro F1 | {macro_f1:.3f} |")
    lines.append(f"| SCDR | {scdr:.1f}% ({scdr_detected}/{scdr_total} changes) |")

    lines.append("\n## Recommendation")
    lines.append(f"> {recommendation}")
    if is_safe:
        lines.append(
            "\nAttribution quality meets the threshold (Macro F1 ≥ 0.75 and SCDR ≥ 70%)."  # noqa: E501
        )
        lines.append(
            "Role classification can be reliably layered on top of the current pipeline."  # noqa: E501
        )
    else:
        lines.append("\nAttribution quality is below threshold.")
        rationale = []
        if macro_f1 < 0.75:
            rationale.append(f"Macro F1 = {macro_f1:.3f} (needs ≥ 0.75)")
        if scdr < 70.0:
            rationale.append(f"SCDR = {scdr:.1f}% (needs ≥ 70%)")
        for r in rationale:
            lines.append(f"- {r}")

    lines.append("\n## Label Mapping (Pyannote → Canonical)")
    lines.append("| Pyannote Label | Canonical Label |")
    lines.append("|----------------|-----------------|")
    for pred_label, canonical in sorted(label_map.items()):
        lines.append(f"| {pred_label} | {canonical} |")

    lines.append("\n## Per-Speaker Precision / Recall / F1")
    lines.append("| Speaker | Precision | Recall | F1 | TP | FP | FN |")
    lines.append("|---------|-----------|--------|----|----|----|----|")
    for spk, m in sorted(per_speaker.items()):
        lines.append(
            f"| {spk} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} "
            f"| {m['tp']} | {m['fp']} | {m['fn']} |"
        )

    if failures:
        lines.append("\n## Failure Analysis (first 10 misattributions)")
        lines.append("| Start | End | Predicted | Expected | Text |")
        lines.append("|-------|-----|-----------|----------|------|")
        for f in failures:
            text_safe = f["text"].encode("ascii", "replace").decode("ascii")
            lines.append(
                f"| {f['start']:.2f} | {f['end']:.2f} "
                f"| {f['predicted_mapped']} (raw: {f['predicted_raw']}) "
                f"| {f['expected']} | {text_safe} |"
            )
    else:
        lines.append(
            "\n## Failure Analysis\nNo misattributions detected in matched segments."
        )

    lines.append("\n---\n*Generated by `evaluate_speaker_accuracy.py`*")
    return "\n".join(lines)


# ── Main entry point ──────────────────────────────────────────────────────────


async def run_evaluation(
    session_id: str,
    gt_path: str,
    output_path: str,
) -> None:
    print(f"Loading ground truth from: {gt_path}")
    annotated_segs, metadata = load_ground_truth(gt_path)
    print(
        f"  Recording: {metadata['recording']}, {len(annotated_segs)} annotated segments"  # noqa: E501
    )

    print(f"\nFetching predicted segments for session {session_id[:8]}...")
    predicted_segs = await fetch_predicted_segments(session_id)
    print(f"  {len(predicted_segs)} predicted segments found in DB")

    coverage = await fetch_coverage(session_id)
    print(f"  Coverage (from session_metrics): {coverage}%")

    print("\nMatching segments...")
    # Use a low overlap threshold (0.10) because DB segments are fine-grained
    # (0.5-2s each) vs Whisper annotation segments (2-6s each). A DB segment
    # covering 10%+ of the annotated window is a valid match.
    pairs = match_segments(predicted_segs, annotated_segs, min_overlap_ratio=0.10)
    print(f"  {len(pairs)} / {len(annotated_segs)} annotated segments matched")

    if not pairs:
        print(
            "ERROR: No segments could be matched. Check timestamps in ground truth file."  # noqa: E501
        )
        sys.exit(1)

    print("\nResolving label mapping...")
    label_map = resolve_label_mapping(pairs)
    for pred_label, canonical in sorted(label_map.items()):
        print(f"  {pred_label} -> {canonical}")

    print("\nComputing metrics...")
    accuracy, correct, total_matched = compute_accuracy(pairs, label_map)
    per_speaker = compute_precision_recall_f1(pairs, label_map)
    scdr, scdr_detected, scdr_total = compute_scdr(
        predicted_segs, annotated_segs, label_map
    )
    failures = collect_failures(pairs, label_map)

    macro_f1 = (
        sum(v["f1"] for v in per_speaker.values()) / len(per_speaker)
        if per_speaker
        else 0.0
    )

    print(f"\n{'='*50}")
    print(f"  Attribution Accuracy : {accuracy:.1f}%  ({correct}/{total_matched})")
    print(f"  Macro F1             : {macro_f1:.3f}")
    print(f"  SCDR                 : {scdr:.1f}%  ({scdr_detected}/{scdr_total})")
    print(f"{'='*50}")

    report = generate_report(
        session_id=session_id,
        recording=metadata["recording"],
        coverage=coverage,
        accuracy=accuracy,
        correct=correct,
        total_matched=total_matched,
        per_speaker=per_speaker,
        scdr=scdr,
        scdr_detected=scdr_detected,
        scdr_total=scdr_total,
        label_map=label_map,
        failures=failures,
        matched_count=len(pairs),
        annotated_count=len(annotated_segs),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate speaker attribution accuracy against a hand-annotated ground truth."  # noqa: E501
    )
    parser.add_argument(
        "--session-id", required=True, help="UUID of the session to evaluate"
    )
    parser.add_argument(
        "--ground-truth", required=True, help="Path to ground truth JSON file"
    )
    parser.add_argument(
        "--output",
        default="speaker_attribution_accuracy_report.md",
        help="Output markdown report path (default: speaker_attribution_accuracy_report.md)",  # noqa: E501
    )
    args = parser.parse_args()

    asyncio.run(
        run_evaluation(
            session_id=args.session_id,
            gt_path=args.ground_truth,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()
