"""Diagnose actual failure patterns in each failing benchmark sample."""
import json
import os
import sys
import subprocess
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

SAMPLE_RATE = 16000
DATASET_ROOT = os.path.join("backend", "benchmark_dataset")
AUDIO_DIR = "sample_audio"

FAILING_SAMPLES = [
    ("2_speaker", "meeting_short"),
    ("2_speaker", "sales_meeting"),
    ("2_speaker", "sales_ambiguous"),
    ("noisy", "meeting_messy"),
    ("noisy", "sales_bad"),
]

def decode_audio(path):
    cmd = ["ffmpeg", "-y", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pcm = proc.stdout.read()
    proc.wait()
    return pcm

def main():
    from backend.core.config import get_settings
    from backend.audio.transcriber import get_transcriber
    from backend.evaluate_speaker_accuracy import (
        Segment as EvalSegment, match_segments, resolve_label_mapping
    )
    import torch, warnings

    settings = get_settings()
    print("Loading models...")
    transcriber = get_transcriber()
    transcriber.load(settings.whisper_model, settings.whisper_compute_type, settings.whisper_device)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=settings.hf_token)
    pipeline.to(torch.device(settings.pyannote_device))

    for cat, name in FAILING_SAMPLES:
        sample_dir = os.path.join(DATASET_ROOT, cat, name)
        gt_path = os.path.join(sample_dir, "ground_truth.json")
        with open(gt_path) as f:
            gt = json.load(f)

        audio_path = os.path.join(AUDIO_DIR, gt["recording"])
        expected_speakers = gt["expected_speakers"]
        pcm = decode_audio(audio_path)

        raw_segments = transcriber.transcribe(pcm, time_offset=0.0)

        audio_int16 = np.frombuffer(pcm, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
        waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}
        diarization = pipeline(waveform, num_speakers=expected_speakers)

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
                except:
                    pass
            turns.append((turn.start, turn.end, mapped))

        predicted = []
        for seg in raw_segments:
            best_speaker, best_ov = "Speaker 1", 0.0
            for t_s, t_e, spk in turns:
                ov = min(seg.end, t_e) - max(seg.start, t_s)
                if ov > best_ov:
                    best_ov = ov
                    best_speaker = spk
            predicted.append(EvalSegment(start=seg.start, end=seg.end, speaker=best_speaker, text=seg.text))

        gt_segs = [EvalSegment(start=s["start"], end=s["end"], speaker=s["speaker"], text=s.get("text",""))
                    for s in gt["segments"]]

        pairs = match_segments(predicted, gt_segs, min_overlap_ratio=0.10)
        label_map = resolve_label_mapping(pairs)

        print(f"\n{'='*80}")
        print(f"  {cat}/{name}  ({len(predicted)} predicted, {len(gt_segs)} GT)")
        print(f"  Label map: {label_map}")
        print(f"{'='*80}")

        # Show predicted sequence with GT comparison
        print(f"\n  {'Idx':>3} {'Start':>7} {'End':>7} {'Dur':>5} {'Pred':>10} {'->Map':>6} {'GT':>4} {'Match':>5} Text")
        print(f"  {'-'*95}")

        for i, pred in enumerate(predicted):
            mapped = label_map.get(pred.speaker, "?")
            # Find matching GT
            gt_match = "?"
            for g in gt_segs:
                ov = min(pred.end, g.end) - max(pred.start, g.start)
                if ov > 0.1:
                    gt_match = g.speaker
                    break
            
            dur = pred.end - pred.start
            match = "OK" if mapped == gt_match else "XX"
            text = pred.text[:50] if pred.text else ""
            print(f"  {i:3d} {pred.start:7.2f} {pred.end:7.2f} {dur:5.1f} {pred.speaker:>10} {mapped:>6} {gt_match:>4} {match:>5} {text}")

        # Show transitions
        print(f"\n  Predicted transitions:")
        prev = None
        for i, p in enumerate(predicted):
            m = label_map.get(p.speaker, "?")
            if m != prev:
                if prev is not None:
                    print(f"    [{i}] {prev} → {m} at {p.start:.1f}s")
                prev = m

        print(f"\n  GT transitions:")
        prev = None
        for i, g in enumerate(gt_segs):
            if g.speaker != prev:
                if prev is not None:
                    print(f"    [{i}] {prev} → {g.speaker} at {g.start:.1f}s")
                prev = g.speaker

        # Identify sandwich patterns
        print(f"\n  Sandwich patterns (A→B→A) in predicted:")
        for i in range(1, len(predicted)-1):
            p = label_map.get(predicted[i-1].speaker, "?")
            c = label_map.get(predicted[i].speaker, "?")
            n = label_map.get(predicted[i+1].speaker, "?")
            if p == n and c != p:
                dur = predicted[i].end - predicted[i].start
                wc = len(predicted[i].text.split()) if predicted[i].text else 0
                print(f"    [{i}] {p}→{c}→{p} dur={dur:.1f}s words={wc} text='{predicted[i].text[:40]}'")

        # Question marks followed by same speaker (missed transition)
        print(f"\n  Missed transitions (question→same speaker):")
        for i in range(len(predicted)-1):
            if predicted[i].text and predicted[i].text.strip().endswith("?"):
                mp = label_map.get(predicted[i].speaker, "?")
                mn = label_map.get(predicted[i+1].speaker, "?")
                if mp == mn:
                    # Check if GT has a transition here
                    gt_at_next = "?"
                    for g in gt_segs:
                        ov = min(predicted[i+1].end, g.end) - max(predicted[i+1].start, g.start)
                        if ov > 0.1:
                            gt_at_next = g.speaker
                            break
                    gt_at_curr = "?"
                    for g in gt_segs:
                        ov = min(predicted[i].end, g.end) - max(predicted[i].start, g.start)
                        if ov > 0.1:
                            gt_at_curr = g.speaker
                            break
                    if gt_at_curr != gt_at_next:
                        print(f"    [{i}→{i+1}] pred={mp}→{mn} GT={gt_at_curr}→{gt_at_next} Q='{predicted[i].text[-40:]}'")

if __name__ == "__main__":
    main()
