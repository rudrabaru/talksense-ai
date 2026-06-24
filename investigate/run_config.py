"""
Phantom Speaker Single-Config Runner

Run ONE Pyannote configuration and print all metrics.
This avoids VRAM accumulation from loading Pyannote multiple times in one process.

Usage:
    python investigate/run_config.py --config A   # Unconstrained
    python investigate/run_config.py --config B   # num_speakers=2
    python investigate/run_config.py --config C   # min=2, max=2
"""
import argparse
import asyncio
import json
import os
import sys
import time
import warnings
import wave
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

GROUND_TRUTH_PATH = "backend/ground_truth/meeting_short_gt.json"
WAV_PATH = (
    r"D:\Code world\Python\SCET Hackathon\talksense-ai\backend"
    r"\session_audio\session_ceff564bc3a0409b.wav"
)
SESSION_ID = "ceff564b-c3a0-409b-9723-c52b4a40547d"

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, "backend")


# ── Shared helpers ────────────────────────────────────────────────────────────

class Seg:
    def __init__(self, start, end, speaker, text=""):
        self.start = start; self.end = end
        self.speaker = speaker; self.text = text
    def dur(self): return max(0.0, self.end - self.start)
    def ov(self, o): return max(0.0, min(self.end, o.end) - max(self.start, o.start))


def load_gt():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    return [Seg(s["start"], s["end"], s["speaker"], s.get("text","")) for s in d["segments"]]


def load_wav():
    import torch
    with wave.open(WAV_PATH, "rb") as w:
        nch, sw, fr, nf = w.getparams()[:4]
        raw = w.readframes(nf)
    a = np.frombuffer(raw, dtype=np.int16)
    if nch > 1: a = a.reshape(-1, nch).mean(1).astype(np.int16)
    f32 = a.astype(np.float32) / 32768.0
    t = torch.from_numpy(f32).unsqueeze(0)
    return {"waveform": t, "sample_rate": fr}, fr, len(a)/fr


async def fetch_db_segs():
    from db.database import AsyncSessionLocal
    from db import crud
    async with AsyncSessionLocal() as db:
        rows = await crud.get_all_transcript_segments(db, SESSION_ID)
    segs = [Seg(r.start_time, r.end_time, r.speaker_id or "Unknown", r.text or "") for r in rows]
    segs.sort(key=lambda s: s.start)
    return segs


def run_pyannote(pipeline, waveform, kwargs):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        diar = pipeline(waveform, **kwargs)
    try:
        from pyannote.audio.pipelines.speaker_diarization import DiarizeOutput
        ann = diar.speaker_diarization if isinstance(diar, DiarizeOutput) else diar
    except ImportError:
        ann = diar
    turns = []
    for turn, _, spk in ann.itertracks(yield_label=True):
        m = spk
        if spk.startswith("SPEAKER_"):
            try: m = f"Speaker {int(spk.split('_')[-1])+1}"
            except: pass
        turns.append(Seg(turn.start, turn.end, m))
    return turns


def assign_speakers(turns, db_segs):
    """Replicate production assignment: overlap then proximity."""
    result = []
    for pred in db_segs:
        best_spk = "Unknown"
        best_ov = 0.0
        for t in turns:
            ov = pred.ov(t)
            if ov > best_ov:
                best_ov = ov; best_spk = t.speaker
        if best_spk == "Unknown" and turns:
            nearest = min(turns, key=lambda t: min(abs(pred.start-t.end), abs(pred.end-t.start)))
            dist = min(abs(pred.start-nearest.end), abs(pred.end-nearest.start))
            if dist < 2.0:
                best_spk = nearest.speaker
        result.append(Seg(pred.start, pred.end, best_spk, pred.text))
    return result


def match_segs(predicted, annotated):
    pairs = []
    for pred in predicted:
        best_ann = None; best_ov = 0.0
        for ann in annotated:
            o = pred.ov(ann)
            if o > best_ov: best_ov = o; best_ann = ann
        if best_ann and pred.dur() > 0 and (best_ov/pred.dur()) >= 0.10:
            pairs.append((pred, best_ann))
    return pairs


def resolve_map(pairs):
    cooc = defaultdict(Counter)
    for p, a in pairs: cooc[p.speaker][a.speaker] += 1
    mp = {}; used = set()
    for pl in sorted(cooc, key=lambda l: sum(cooc[l].values()), reverse=True):
        best_c = None; best_n = 0
        for c, n in cooc[pl].most_common():
            if c not in used and n > best_n: best_n = n; best_c = c
        if best_c: mp[pl] = best_c; used.add(best_c)
        else: mp[pl] = f"_unmapped_{pl}"
    return mp


def compute_metrics(pairs, label_map, assigned, annotated):
    all_c = set(a.speaker for _, a in pairs)
    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    correct = 0
    for p, a in pairs:
        mapped = label_map.get(p.speaker, f"_unmapped_{p.speaker}")
        if mapped == a.speaker:
            tp[a.speaker] += 1; correct += 1
        else:
            fp[mapped] += 1; fn[a.speaker] += 1

    per_spk = {}
    for spk in all_c:
        t = tp[spk]; pc = t+fp[spk]; rc = t+fn[spk]
        p = (t/pc) if pc>0 else 0.0; r = (t/rc) if rc>0 else 0.0
        f1 = (2*p*r/(p+r)) if (p+r)>0 else 0.0
        per_spk[spk] = {"precision": round(p,3), "recall": round(r,3), "f1": round(f1,3)}

    macro_f1 = sum(v["f1"] for v in per_spk.values()) / len(per_spk) if per_spk else 0.0

    # SCDR
    def get_changes(segs, use_map=False):
        ch = []
        for i in range(1, len(segs)):
            p, q = segs[i-1].speaker, segs[i].speaker
            if use_map: p, q = label_map.get(p,p), label_map.get(q,q)
            if p != q: ch.append((segs[i-1].end + segs[i].start)/2)
        return ch
    ann_ch = get_changes(annotated)
    pred_ch = get_changes(assigned, use_map=True)
    used_j = set(); det = 0
    for ac in ann_ch:
        for j, pc2 in enumerate(pred_ch):
            if j not in used_j and abs(pc2-ac) <= 0.5:
                det += 1; used_j.add(j); break
    scdr = round((det/len(ann_ch)*100) if ann_ch else 0.0, 1)

    coverage = round(sum(1 for s in assigned if s.speaker not in ("Unknown",""))/max(len(assigned),1)*100, 1)
    acc = round(correct/max(len(pairs),1)*100, 1)

    return {
        "accuracy": acc, "correct": correct, "total": len(pairs),
        "macro_f1": round(macro_f1, 3),
        "scdr": scdr, "scdr_det": det, "scdr_tot": len(ann_ch),
        "coverage": coverage,
        "per_speaker": per_spk,
    }


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["A","B","C"], required=True)
    args = parser.parse_args()

    config_map = {
        "A": {"name": "A) Unconstrained",       "kwargs": {}},
        "B": {"name": "B) num_speakers=2",       "kwargs": {"num_speakers": 2}},
        "C": {"name": "C) min=2,max=2",          "kwargs": {"min_speakers": 2, "max_speakers": 2}},
    }
    cfg = config_map[args.config]

    print(f"Config: {cfg['name']}  kwargs={cfg['kwargs']}")

    annotated = load_gt()
    waveform, fr, dur = load_wav()
    print(f"WAV: {dur:.1f}s @ {fr}Hz")

    db_segs = await fetch_db_segs()
    print(f"DB segments: {len(db_segs)}")

    print("Loading Pyannote...")
    from audio.diarizer import get_diarizer
    from core.config import get_settings
    settings = get_settings()
    d = get_diarizer()
    if not d._loaded:
        d.load(hf_token=settings.hf_token, device=settings.pyannote_device)
    if not d._loaded:
        print("ERROR: Pyannote not loaded"); sys.exit(1)

    print(f"Running Pyannote with kwargs={cfg['kwargs']}...")
    t0 = time.monotonic()
    turns = run_pyannote(d._pipeline, waveform, cfg["kwargs"])
    elapsed = time.monotonic() - t0

    unique_spks = list({t.speaker for t in turns})
    print(f"Done in {elapsed:.1f}s — speakers={unique_spks} turns={len(turns)}")

    assigned = assign_speakers(turns, db_segs)
    pairs = match_segs(assigned, annotated)
    label_map = resolve_map(pairs)
    metrics = compute_metrics(pairs, label_map, assigned, annotated)

    print(f"\nLabel mapping: {label_map}")
    print(f"Coverage   : {metrics['coverage']}%")
    print(f"Accuracy   : {metrics['accuracy']}% ({metrics['correct']}/{metrics['total']})")
    print(f"Macro F1   : {metrics['macro_f1']}")
    print(f"SCDR       : {metrics['scdr']}% ({metrics['scdr_det']}/{metrics['scdr_tot']})")
    print("\nPer-speaker:")
    for spk, m in sorted(metrics["per_speaker"].items()):
        print(f"  {spk}: P={m['precision']} R={m['recall']} F1={m['f1']}")

    # Write result JSON for aggregation
    result = {
        "config": cfg["name"],
        "kwargs": str(cfg["kwargs"]),
        "elapsed_s": round(elapsed, 1),
        "speakers_detected": len(unique_spks),
        "speaker_labels": unique_spks,
        "turns": len(turns),
        **metrics,
    }
    out_path = f"investigate/result_config_{args.config}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(run())
