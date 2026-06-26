import argparse
import asyncio
import json
import sys
from collections import Counter
from typing import Any, Dict, List

from db import crud
from db.database import AsyncSessionLocal


async def fetch_attribution_metrics(session_id: str) -> Dict:
    async with AsyncSessionLocal() as db:
        metrics = await crud.get_latest_session_metrics(db, session_id)
        attribution = {}
        for m in metrics:
            if m.metric_name == "speaker_attribution":
                attribution = m.metric_value or {}
                break
        return attribution


async def fetch_transcript_segments(session_id: str) -> List:
    async with AsyncSessionLocal() as db:
        segments = await crud.get_all_transcript_segments(db, session_id)
        return segments


def compute_speaker_distribution(segments) -> Dict[str, int]:
    cnt = Counter()
    for seg in segments:
        speaker = seg.speaker_id or "Unknown"
        cnt[speaker] += 1
    return dict(cnt)


def compute_speaker_change_stats(segments) -> Dict:
    changes = 0
    total = 0
    prev_speaker = None
    for seg in sorted(segments, key=lambda s: s.start_time):
        speaker = seg.speaker_id or "Unknown"
        if prev_speaker is not None and speaker != prev_speaker:
            changes += 1
        prev_speaker = speaker
        total += 1
    return {"speaker_changes": changes, "total_segments": total}


async def evaluate_session(
    session_id: str, ground_truth: Dict[str, Any] | None
) -> Dict[str, Any]:
    attribution = await fetch_attribution_metrics(session_id)
    segments = await fetch_transcript_segments(session_id)
    distribution = compute_speaker_distribution(segments)
    change_stats = compute_speaker_change_stats(segments)

    total_segments = change_stats["total_segments"]
    changes = change_stats["speaker_changes"]
    scdr = (changes / (total_segments - 1)) * 100 if total_segments > 1 else 0.0
    coverage = attribution.get("coverage_percent", 0.0)
    speakers_detected = attribution.get("speakers_detected", len(distribution))
    speaker_turns = attribution.get("speaker_turns", 0)

    result = {
        "session_id": session_id,
        "coverage": coverage,
        "speakers_detected": speakers_detected,
        "speaker_turns": speaker_turns,
        "total_segments": total_segments,
        "speaker_changes": changes,
        "scdr": scdr,
        "distribution": distribution,
        "ground_truth": ground_truth,
        "is_safe": coverage >= 80.0,
    }

    if ground_truth:
        exp_speakers = len(ground_truth.get("expected_speakers", []))
        exp_changes = ground_truth.get("expected_changes", 0)

        # Calculate accuracies safely
        speaker_acc = (
            (
                min(speakers_detected, exp_speakers)
                / max(speakers_detected, exp_speakers)
                * 100
            )
            if exp_speakers and speakers_detected
            else 0.0
        )
        change_acc = (
            (min(changes, exp_changes) / max(changes, exp_changes) * 100)
            if exp_changes and changes
            else 0.0
        )

        result["speaker_accuracy"] = speaker_acc
        result["change_accuracy"] = change_acc

    return result


async def run_batch_evaluation(
    session_ids: List[str], truth_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    tasks = [evaluate_session(sid, truth_data.get(sid)) for sid in session_ids]
    return await asyncio.gather(*tasks)


def generate_markdown_report(results: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("# Speaker Attribution Evaluation Report")
    lines.append("## Overview")

    total_sessions = len(results)
    if total_sessions == 0:
        return "# Error: No sessions evaluated"

    avg_coverage = sum(r["coverage"] for r in results) / total_sessions
    avg_scdr = sum(r["scdr"] for r in results) / total_sessions

    with_truth = [r for r in results if r["ground_truth"]]
    if with_truth:
        avg_spk_acc = sum(r.get("speaker_accuracy", 0.0) for r in with_truth) / len(
            with_truth
        )
        avg_chg_acc = sum(r.get("change_accuracy", 0.0) for r in with_truth) / len(
            with_truth
        )
    else:
        avg_spk_acc = None
        avg_chg_acc = None

    failures = [r for r in results if not r["is_safe"]]

    lines.append(f"- **Sessions Evaluated**: {total_sessions}")
    lines.append(f"- **Average Coverage**: {avg_coverage:.1f}%")
    lines.append(f"- **Average SCDR**: {avg_scdr:.1f}%")
    if avg_spk_acc is not None:
        lines.append(f"- **Average Speaker Count Accuracy**: {avg_spk_acc:.1f}%")
        lines.append(f"- **Average Change Detection Accuracy**: {avg_chg_acc:.1f}%")

    lines.append("\n## Recommendation")
    # Condition: Avg Coverage > 80%, and if ground truth is present, reasonably high
    # change accuracy.
    is_safe = avg_coverage >= 80.0
    if with_truth and avg_chg_acc is not None and avg_chg_acc < 70.0:
        is_safe = False

    if is_safe:
        lines.append("> **Role Classification Safe**")
        lines.append(
            "\nSpeaker attribution quality is sufficient to support role classification."  # noqa: E501
        )
    else:
        lines.append("> **Role Classification Not Yet Safe**")
        lines.append(
            "\nSpeaker attribution requires further tuning before role classification can be reliable."  # noqa: E501
        )

    if failures:
        lines.append("\n## Failure Analysis")
        for f in failures:
            lines.append(
                f"- **Session `{f['session_id']}`**: Coverage {f['coverage']:.1f}% (< 80%)"  # noqa: E501
            )

    lines.append("\n## Per-Recording Results")
    for r in results:
        lines.append(f"### Session: `{r['session_id']}`")
        lines.append(f"- **Coverage**: {r['coverage']:.1f}%")
        lines.append(f"- **Speakers Detected**: {r['speakers_detected']}")
        lines.append(
            f"- **Speaker Changes**: {r['speaker_changes']} (SCDR: {r['scdr']:.1f}%)"
        )

        if r["ground_truth"]:
            gt = r["ground_truth"]
            lines.append("- **Ground Truth Comparison**:")
            lines.append(
                f"  - Expected Speakers: {len(gt.get('expected_speakers', []))} (Accuracy: {r.get('speaker_accuracy', 0):.1f}%)"  # noqa: E501
            )
            lines.append(
                f"  - Expected Changes: {gt.get('expected_changes', 0)} (Accuracy: {r.get('change_accuracy', 0):.1f}%)"  # noqa: E501
            )

        dist_str = ", ".join([f"{k}: {v}" for k, v in r["distribution"].items()])
        lines.append(f"- **Distribution**: {dist_str}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate speaker attribution for TalkSense sessions."
    )
    parser.add_argument(
        "session_ids", nargs="+", help="UUID(s) of the session(s) to evaluate"
    )
    parser.add_argument(
        "--ground-truth",
        help="Path to JSON file containing ground truth data",
        default=None,
    )

    args = parser.parse_args()

    truth_data = {}
    if args.ground_truth:
        try:
            with open(args.ground_truth, "r") as f:
                truth_data = json.load(f)
        except Exception as e:
            print(f"Failed to load ground truth file: {e}")
            sys.exit(1)

    results = asyncio.run(run_batch_evaluation(args.session_ids, truth_data))
    report = generate_markdown_report(results)

    report_file = "speaker_attribution_evaluation_report.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"Evaluation complete. Report generated at: {report_file}")


if __name__ == "__main__":
    main()
