from typing import List, Tuple, Dict
from collections import defaultdict, Counter
from experimental.benchmark.common_schema import Segment

def match_segments(
    predicted: List[Segment],
    annotated: List[Segment],
    min_overlap_ratio: float = 0.10,
) -> List[Tuple[Segment, Segment]]:
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


def resolve_label_mapping(pairs: List[Tuple[Segment, Segment]]) -> Dict[str, str]:
    cooc: Dict[str, Counter] = defaultdict(Counter)
    for pred_seg, ann_seg in pairs:
        cooc[pred_seg.speaker][ann_seg.speaker] += 1

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
            mapping[pred_label] = f"_unmapped_{pred_label}"
    return mapping


def compute_accuracy(
    pairs: List[Tuple[Segment, Segment]],
    label_map: Dict[str, str],
) -> Tuple[float, int, int]:
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
        }
    return results


def compute_scdr(
    predicted: List[Segment],
    annotated: List[Segment],
    label_map: Dict[str, str],
    tolerance_sec: float = 0.5,
) -> Tuple[float, int, int]:
    def get_changes(segs: List[Segment], use_map: bool = False):
        changes = []
        for i in range(1, len(segs)):
            prev_spk = segs[i - 1].speaker
            curr_spk = segs[i].speaker
            if use_map:
                prev_spk = label_map.get(prev_spk, prev_spk)
                curr_spk = label_map.get(curr_spk, curr_spk)
            if prev_spk != curr_spk:
                midpoint = (segs[i - 1].end + segs[i].start) / 2
                changes.append({"time": midpoint, "prev": prev_spk, "next": curr_spk})
        return changes

    annotated_changes = get_changes(annotated, use_map=False)
    predicted_changes = get_changes(predicted, use_map=True)

    correctly_detected = 0
    used_predicted_changes = set()

    for ann_change in annotated_changes:
        for j, pred_change in enumerate(predicted_changes):
            err = abs(pred_change["time"] - ann_change["time"])
            if j not in used_predicted_changes and err <= tolerance_sec:
                correctly_detected += 1
                used_predicted_changes.add(j)
                break

    total_annotated = len(annotated_changes)
    scdr = (correctly_detected / total_annotated * 100) if total_annotated > 0 else 0.0
    return scdr, correctly_detected, total_annotated
