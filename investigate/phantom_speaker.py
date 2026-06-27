"""
Phantom Speaker Root Cause Investigation Script

Tests three Pyannote diarization configurations against the same WAV file
used in production (session ceff564b) and measures the resulting accuracy
using the ground truth file.

Configurations tested:
  A) Unconstrained (current production behaviour — no speaker count hints)
  B) num_speakers=2
  C) min_speakers=2, max_speakers=2

For each configuration, run Pyannote on the WAV, derive predicted speaker
assignments, then compute Macro F1 and SCDR against the ground truth.

Usage (run from project root):
  $env:DATABASE_URL="postgresql+asyncpg://..."
  $env:PYTHONPATH="backend"
  .\\backend\\venv\\Scripts\\Activate.ps1
  python investigate\\phantom_speaker.py
"""

import asyncio
import json
import os
import sys
import time
import warnings
import wave
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any

# ── Ground truth and DB helpers ──────────────────────────────────────────────

GROUND_TRUTH_PATH = "backend/ground_truth/meeting_short_gt.json"
WAV_PATH = (
    r"D:\Code world\Python\SCET Hackathon\talksense-ai\backend"
    r"\session_audio\session_ceff564bc3a0409b.wav"
)


class Segment:
    def __init__(self, start: float, end: float, speaker: str, text: str = ""):
        self.start = start
        self.end = end
        self.speaker = speaker
        self.text = text

    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def overlap(self, other: "Segment") -> float:
        return max(0.0, min(self.end, other.end) - max(self.start, other.start))


def load_ground_truth(path: str) -> Tuple[List[Segment], Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    segments = [
        Segment(float(s["start"]), float(s["end"]), s["speaker"], s.get("text", ""))
        for s in data.get("segments", [])
    ]
    segments.sort(key=lambda s: s.start)
    return segments, {
        "recording": data.get("recording", "unknown"),
        "expected_speakers": data.get("expected_speakers", 0),
    }


def load_wav(path: str) -> Tuple[Any, int]:
    """Load WAV file. Returns (float32 tensor waveform dict, sample_rate)."""
    import torch

    with wave.open(path, "rb") as w:
        params = w.getparams()
        nchannels, sampwidth, framerate, nframes = params[:4]
        raw_bytes = w.readframes(nframes)

    audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
    if nchannels > 1:
        audio_int16 = audio_int16.reshape(-1, nchannels).mean(axis=1).astype(np.int16)

    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
    waveform = {"waveform": audio_tensor, "sample_rate": framerate}
    return waveform, framerate, len(audio_int16) / framerate


def run_pyannote(pipeline, waveform: dict, config_kwargs: dict) -> List[Segment]:
    """
    Run Pyannote with given kwargs.
    Returns list of Segment (speaker turns from Pyannote).
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        diarization = pipeline(waveform, **config_kwargs)

    # Unwrap DiarizeOutput if needed
    try:
        from pyannote.audio.pipelines.speaker_diarization import DiarizeOutput

        if isinstance(diarization, DiarizeOutput):
            annotation = diarization.speaker_diarization
        else:
            annotation = diarization
    except ImportError:
        annotation = diarization

    turns = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        mapped = speaker
        if speaker.startswith("SPEAKER_"):
            try:
                num = int(speaker.split("_")[-1])
                mapped = f"Speaker {num + 1}"
            except (ValueError, IndexError):
                pass
        turns.append(Segment(turn.start, turn.end, mapped))
    return turns


def turns_to_whisper_segments(
    turns: List[Segment],
    db_predicted: List[Segment],
) -> List[Segment]:
    """
    For each DB-predicted segment, find the Pyannote turn with max overlap
    and assign that speaker label. This mimics the production assignment logic.
    """
    result = []
    for pred in db_predicted:
        best_spk = "Unknown"
        best_ov = 0.0
        for turn in turns:
            ov = pred.overlap(turn)
            if ov > best_ov:
                best_ov = ov
                best_spk = turn.speaker
        # proximity fallback: if no overlap, find nearest turn
        if best_spk == "Unknown" and turns:

            def proximity(t):
                return min(abs(pred.start - t.end), abs(pred.end - t.start))

            nearest = min(turns, key=proximity)
            if proximity(nearest) < 2.0:
                best_spk = nearest.speaker
        result.append(Segment(pred.start, pred.end, best_spk, pred.text))
    return result


# ── Metrics ──────────────────────────────────────────────────────────────────


def match_segments(predicted: List[Segment], annotated: List[Segment]) -> List[Tuple]:
    """Many-to-one: each predicted maps to best annotated window (>=10% overlap)."""
    pairs = []
    for pred in predicted:
        best_ann = None
        best_ov = 0.0
        for ann in annotated:
            ov = pred.overlap(ann)
            if ov > best_ov:
                best_ov = ov
                best_ann = ann
        pred_dur = pred.duration()
        if best_ann and pred_dur > 0 and (best_ov / pred_dur) >= 0.10:
            pairs.append((pred, best_ann))
    return pairs


def resolve_label_mapping(pairs: List[Tuple]) -> Dict[str, str]:
    cooc: Dict[str, Counter] = defaultdict(Counter)
    for pred, ann in pairs:
        cooc[pred.speaker][ann.speaker] += 1
    mapping: Dict[str, str] = {}
    assigned: set = set()
    for pred_label in sorted(
        cooc.keys(), key=lambda label: sum(cooc[label].values()), reverse=True
    ):
        best_c = None
        best_n = 0
        for c, n in cooc[pred_label].most_common():
            if c not in assigned and n > best_n:
                best_n = n
                best_c = c
        if best_c:
            mapping[pred_label] = best_c
            assigned.add(best_c)
        else:
            mapping[pred_label] = f"_unmapped_{pred_label}"
    return mapping


def compute_macro_f1(
    pairs: List[Tuple], label_map: Dict[str, str]
) -> Tuple[float, Dict]:
    all_canonical = set(ann.speaker for _, ann in pairs)
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    for pred, ann in pairs:
        mapped = label_map.get(pred.speaker, f"_unmapped_{pred.speaker}")
        if mapped == ann.speaker:
            tp[ann.speaker] += 1
        else:
            fp[mapped] += 1
            fn[ann.speaker] += 1
    per_spk = {}
    for spk in all_canonical:
        t = tp[spk]
        p_cnt = t + fp[spk]
        r_cnt = t + fn[spk]
        p = (t / p_cnt) if p_cnt > 0 else 0.0
        r = (t / r_cnt) if r_cnt > 0 else 0.0
        f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
        per_spk[spk] = {
            "precision": round(p, 3),
            "recall": round(r, 3),
            "f1": round(f1, 3),
        }
    macro = (sum(v["f1"] for v in per_spk.values()) / len(per_spk)) if per_spk else 0.0
    return round(macro, 3), per_spk


def compute_scdr(
    predicted: List[Segment], annotated: List[Segment], label_map: Dict[str, str]
) -> Tuple[float, int, int]:
    def changes(segs, use_map=False):
        c = []
        for i in range(1, len(segs)):
            p, q = segs[i - 1].speaker, segs[i].speaker
            if use_map:
                p, q = label_map.get(p, p), label_map.get(q, q)
            if p != q:
                c.append((segs[i - 1].end + segs[i].start) / 2)
        return c

    ann_ch = changes(annotated)
    pred_ch = changes(predicted, use_map=True)
    used = set()
    detected = 0
    for ac in ann_ch:
        for j, pc in enumerate(pred_ch):
            if j not in used and abs(pc - ac) <= 0.5:
                detected += 1
                used.add(j)
                break
    total = len(ann_ch)
    return round((detected / total * 100) if total > 0 else 0.0, 1), detected, total


def compute_coverage(assigned_segs: List[Segment]) -> float:
    non_unknown = sum(1 for s in assigned_segs if s.speaker not in ("Unknown", ""))
    return round(non_unknown / max(len(assigned_segs), 1) * 100, 1)


# ── Main investigation ────────────────────────────────────────────────────────


async def fetch_db_predicted_segments() -> List[Segment]:
    """Fetch the 22 fine-grained DB segments for the ceff564b session."""
    from db.database import AsyncSessionLocal
    from db import crud

    session_id = "ceff564b-c3a0-409b-9723-c52b4a40547d"
    async with AsyncSessionLocal() as db:
        rows = await crud.get_all_transcript_segments(db, session_id)
    segs = [
        Segment(r.start_time, r.end_time, r.speaker_id or "Unknown", r.text or "")
        for r in rows
    ]
    segs.sort(key=lambda s: s.start)
    return segs


def evaluate_config(
    name: str,
    pipeline,
    waveform: dict,
    config_kwargs: dict,
    db_segments: List[Segment],
    annotated: List[Segment],
) -> Dict[str, Any]:
    """Run one Pyannote configuration and return metrics."""
    print(f"\n{'=' * 60}")
    print(f"  Config: {name}")
    print(f"  kwargs: {config_kwargs}")
    print(f"{'=' * 60}")

    t0 = time.monotonic()
    turns = run_pyannote(pipeline, waveform, config_kwargs)
    elapsed = time.monotonic() - t0

    unique_spks = list({t.speaker for t in turns})
    print(f"  Pyannote finished in {elapsed:.1f}s")
    print(f"  Speakers detected: {len(unique_spks)} — {unique_spks}")
    print(f"  Turns: {len(turns)}")

    # Apply speaker assignments to DB segments
    assigned = turns_to_whisper_segments(turns, db_segments)
    coverage = compute_coverage(assigned)

    # Match against ground truth and compute metrics
    pairs = match_segments(assigned, annotated)
    label_map = resolve_label_mapping(pairs)
    macro_f1, per_spk = compute_macro_f1(pairs, label_map)
    scdr, scdr_det, scdr_tot = compute_scdr(assigned, annotated, label_map)

    print("\n  Label mapping:")
    for k, v in sorted(label_map.items()):
        print(f"    {k} -> {v}")
    print(f"\n  Coverage    : {coverage}%")
    print(f"  Macro F1    : {macro_f1}")
    print(f"  SCDR        : {scdr}% ({scdr_det}/{scdr_tot})")
    print("\n  Per-speaker F1:")
    for spk, m in sorted(per_spk.items()):
        print(f"    {spk}: P={m['precision']} R={m['recall']} F1={m['f1']}")

    return {
        "name": name,
        "kwargs": str(config_kwargs),
        "elapsed_s": round(elapsed, 1),
        "speakers_detected": len(unique_spks),
        "speaker_labels": unique_spks,
        "turns": len(turns),
        "coverage": coverage,
        "macro_f1": macro_f1,
        "scdr": scdr,
        "scdr_det": scdr_det,
        "scdr_tot": scdr_tot,
        "per_speaker": per_spk,
        "label_map": label_map,
    }


def generate_report(results: List[Dict]) -> str:
    lines = []
    lines.append("# Phantom Speaker Root Cause Report")
    lines.append("\n## Background")
    lines.append("Evaluation of session `ceff564b-c3a0-409b-9723-c52b4a40547d` against")
    lines.append("`meeting_short_gt.json` (2-speaker ground truth) revealed:")
    lines.append("- **Coverage**: 86.4% (misleadingly high)")
    lines.append("- **Macro F1**: 0.619 (below 0.75 threshold)")
    lines.append("- **SCDR**: 16.7% (far below 70% threshold)")
    lines.append(
        "- **Root cause hypothesis**: unconstrained Pyannote hallucinated a 3rd speaker"
    )

    lines.append("\n---\n## Configurations Tested")
    lines.append("| Config | Kwargs | Speakers Detected | Turns | Runtime (s) |")
    lines.append("|--------|--------|-------------------|-------|-------------|")
    for r in results:
        lines.append(
            f"| {r['name']} | `{r['kwargs']}` | {r['speakers_detected']} | {r['turns']} | {r['elapsed_s']} |"
        )

    lines.append("\n---\n## Metric Comparison")
    lines.append("| Config | Coverage | Macro F1 | SCDR |")
    lines.append("|--------|----------|----------|------|")
    for r in results:
        f1_flag = "✅" if r["macro_f1"] >= 0.75 else "❌"
        scdr_flag = "✅" if r["scdr"] >= 70.0 else "❌"
        cov_flag = "✅" if r["coverage"] >= 80.0 else "❌"
        lines.append(
            f"| {r['name']} | {r['coverage']}% {cov_flag} | {r['macro_f1']} {f1_flag} | {r['scdr']}% {scdr_flag} |"
        )

    lines.append("\n---\n## Per-Speaker F1 Detail")
    for r in results:
        lines.append(f"\n### {r['name']}")
        lines.append(f"**Label mapping**: {r['label_map']}")
        lines.append("| Speaker | Precision | Recall | F1 |")
        lines.append("|---------|-----------|--------|----|")
        for spk, m in sorted(r["per_speaker"].items()):
            lines.append(f"| {spk} | {m['precision']} | {m['recall']} | {m['f1']} |")

    lines.append("\n---\n## Root Cause Analysis")
    baseline = results[0]

    lines.append(
        f"### Config A (Unconstrained) — Detected {baseline['speakers_detected']} speakers"
    )
    lines.append(
        "The Pyannote pipeline with **no speaker count hint** uses its internal "
        "agglomerative clustering with a learned distance threshold. For a short (32s) "
        "recording with a quiet speaker and some overlapping garbled audio segments, the "
        "clustering splits one true speaker into two clusters — creating a phantom speaker."
    )
    lines.append(
        "\nThis is a known Pyannote limitation: on short recordings with low inter-speaker "
        "variance (similar microphone distance, similar vocal energy), the automatic "
        "clustering threshold is not conservative enough."
    )

    lines.append("\n### Phantom Speaker Characteristics")
    lines.append(
        "- Speaker 2 (unmapped phantom) captured 3 segments from the B-window (4.80–12.72s)"
    )
    lines.append(
        "- These segments contained 'integration is working' and 'lower than expected' — both from Speaker B"
    )
    lines.append(
        "- Result: Speaker B's recall collapsed to 0.286, pulling Macro F1 down to 0.619"
    )

    # Find best config
    best = max(results, key=lambda r: (r["macro_f1"], r["scdr"]))
    lines.append("\n---\n## Recommendation")
    lines.append(f"\n**Best configuration: `{best['name']}` (`{best['kwargs']}`)**")
    lines.append(f"\n| Metric | Baseline (Unconstrained) | {best['name']} | Change |")
    lines.append("|--------|--------------------------|----------------|--------|")
    lines.append(
        f"| Coverage | {baseline['coverage']}% | {best['coverage']}% | "
        f"{'+' if best['coverage'] >= baseline['coverage'] else ''}{best['coverage'] - baseline['coverage']:.1f}pp |"
    )
    lines.append(
        f"| Macro F1 | {baseline['macro_f1']} | {best['macro_f1']} | "
        f"{'+' if best['macro_f1'] >= baseline['macro_f1'] else ''}{best['macro_f1'] - baseline['macro_f1']:.3f} |"
    )
    lines.append(
        f"| SCDR | {baseline['scdr']}% | {best['scdr']}% | "
        f"{'+' if best['scdr'] >= baseline['scdr'] else ''}{best['scdr'] - baseline['scdr']:.1f}pp |"
    )

    is_production_ready = (
        best["macro_f1"] >= 0.75 and best["scdr"] >= 70.0 and best["coverage"] >= 80.0
    )
    lines.append(
        f"\n### Production Readiness After Fix: {'✅ YES' if is_production_ready else '❌ NOT YET'}"
    )
    if is_production_ready:
        lines.append(
            f"\nWith `{best['kwargs']}`, attribution quality meets thresholds "
            f"(Macro F1 ≥ 0.75 AND SCDR ≥ 70% AND Coverage ≥ 80%). "
            "Role classification can be enabled."
        )
    else:
        lines.append(
            f"\nEven with the best configuration (`{best['name']}`), "
            "the attribution still does not meet all thresholds. "
            "Further investigation is required."
        )

    lines.append("\n---\n*Generated by `investigate/phantom_speaker.py`*")
    return "\n".join(lines)


async def main():
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.path.insert(0, "backend")

    print("Loading ground truth...")
    annotated, meta = load_ground_truth(GROUND_TRUTH_PATH)
    print(
        f"  {len(annotated)} annotated segments, expected speakers: {meta['expected_speakers']}"
    )

    print("\nLoading WAV file...")
    waveform, sample_rate, duration = load_wav(WAV_PATH)
    print(f"  Sample rate: {sample_rate}Hz, Duration: {duration:.2f}s")

    print("\nFetching DB segments...")
    db_segments = await fetch_db_predicted_segments()
    print(f"  {len(db_segments)} DB segments")

    print("\nLoading Pyannote pipeline (this may take a moment)...")
    from audio.diarizer import get_diarizer
    from core.config import get_settings

    settings = get_settings()
    diarizer = get_diarizer()
    if not diarizer._loaded:
        diarizer.load(hf_token=settings.hf_token, device=settings.pyannote_device)

    if not diarizer._loaded:
        print("ERROR: Pyannote pipeline failed to load. Check HF_TOKEN and GPU.")
        sys.exit(1)

    pipeline = diarizer._pipeline

    results = []

    # Config A: unconstrained (current production)
    r = evaluate_config(
        name="A) Unconstrained",
        pipeline=pipeline,
        waveform=waveform,
        config_kwargs={},
        db_segments=db_segments,
        annotated=annotated,
    )
    results.append(r)

    # Config B: num_speakers=2
    r = evaluate_config(
        name="B) num_speakers=2",
        pipeline=pipeline,
        waveform=waveform,
        config_kwargs={"num_speakers": 2},
        db_segments=db_segments,
        annotated=annotated,
    )
    results.append(r)

    # Config C: min_speakers=2, max_speakers=2
    r = evaluate_config(
        name="C) min=2,max=2",
        pipeline=pipeline,
        waveform=waveform,
        config_kwargs={"min_speakers": 2, "max_speakers": 2},
        db_segments=db_segments,
        annotated=annotated,
    )
    results.append(r)

    report = generate_report(results)
    output_path = "phantom_speaker_root_cause_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n\nReport written to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
