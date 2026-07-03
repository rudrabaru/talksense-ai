import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluate_speaker_accuracy import Segment, match_segments, resolve_label_mapping
from run_full_benchmark import decode_audio
from services.word_speaker_aligner import align_words_to_speakers


def load_dataset():
    dataset_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "benchmark_dataset"
    )
    categories = ["2_speaker", "3_speaker", "4_speaker", "noisy", "long_form"]
    samples = []
    for category in categories:
        cat_dir = os.path.join(dataset_root, category)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            sample_dir = os.path.join(cat_dir, name)
            gt_path = os.path.join(sample_dir, "ground_truth.json")
            if os.path.isdir(sample_dir) and os.path.isfile(gt_path):
                with open(gt_path, "r", encoding="utf-8") as f:
                    gt = json.load(f)
                with open(
                    os.path.join(sample_dir, "metadata.json"), "r", encoding="utf-8"
                ) as f:
                    meta = json.load(f)

                audio_file = gt.get(
                    "recording", gt[0].get("recording") if isinstance(gt, list) else ""
                )
                samples.append(
                    {
                        "audio_path": audio_file,
                        "ground_truth": (
                            gt.get("ground_truth", gt) if isinstance(gt, dict) else gt
                        ),
                        "expected_speakers": meta.get("expected_speakers", 2),
                    }
                )
    return samples


def get_changes(segs, label_map=None):
    changes = []
    for i in range(1, len(segs)):
        prev_spk = segs[i - 1].speaker
        curr_spk = segs[i].speaker
        if label_map:
            prev_spk = label_map.get(prev_spk, prev_spk)
            curr_spk = label_map.get(curr_spk, curr_spk)
        if prev_spk != curr_spk:
            midpoint = (segs[i - 1].end + segs[i].start) / 2
            changes.append({"time": midpoint, "prev": prev_spk, "next": curr_spk})
    return changes


def run_ledger():
    os.environ["USE_WORD_LEVEL_ALIGNMENT"] = "1"
    os.environ["ENABLE_POST_PROCESSING"] = "1"
    os.environ["DISABLE_5_WORD_SMOOTHING"] = "1"

    print("Loading models...")
    transcriber = WhisperModel("base", device="cpu", compute_type="int8")
    from core.config import get_settings

    settings = get_settings()
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", token=settings.hf_token
    )
    assert pipeline is not None
    pipeline.to(torch.device("cpu"))

    dataset = load_dataset()
    audio_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "sample_audio")
    )

    print("# TRANSITION CONFUSION LEDGER\n")
    print(
        "| Sample | GT Time | GT Prev->Next | Pred Time | Pred Prev->Next | Err (ms) | Match? | ID Match? | SCDR Match? | Error Type |"
    )
    print(
        "|--------|---------|---------------|-----------|-----------------|----------|--------|-----------|-------------|------------|"
    )

    for item in dataset:
        audio_path = os.path.join(audio_dir, Path(item["audio_path"]).name)

        gt_list = item["ground_truth"]
        if isinstance(gt_list, dict):
            # In case it's a dict that didn't get unpacked
            gt_list = gt_list.get("ground_truth", [])
        annotated = [Segment(**s) for s in gt_list if isinstance(s, dict)]

        pcm = decode_audio(audio_path)
        segments, _ = transcriber.transcribe(audio_path, word_timestamps=True)
        words = []
        for segment in segments:
            if not segment.words:
                continue
            for word in segment.words:
                words.append(
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "confidence": word.probability,
                    }
                )

        audio_int16 = np.frombuffer(pcm, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
        waveform = {"waveform": audio_tensor, "sample_rate": 16000}

        diarization = pipeline(waveform, num_speakers=item.get("expected_speakers", 2))
        assert diarization is not None
        diarization_list = [
            (turn.start, turn.end, speaker)
            for turn, _, speaker in diarization.itertracks(  # pyright: ignore[reportAttributeAccessIssue]
                yield_label=True
            )
        ]

        predicted_dicts = align_words_to_speakers(words, diarization_list)
        predicted = [
            Segment(
                start=d["start"], end=d["end"], speaker=d["speaker"], text=d["word"]
            )
            for d in predicted_dicts
        ]

        pairs = match_segments(predicted, annotated)
        label_map = resolve_label_mapping(pairs)

        gt_changes = get_changes(annotated)
        pred_changes = get_changes(predicted, label_map)

        used_pred = set()

        for gt in gt_changes:
            closest_pred = None
            closest_idx = -1
            min_err = float("inf")

            for j, p in enumerate(pred_changes):
                err = abs(p["time"] - gt["time"])
                if err < min_err:
                    min_err = err
                    closest_pred = p
                    closest_idx = j

            err_ms = min_err * 1000 if closest_pred else -1
            timing_match = min_err <= 0.5 if closest_pred else False

            id_match = False
            if closest_pred:
                id_match = (
                    closest_pred["prev"] == gt["prev"]
                    and closest_pred["next"] == gt["next"]
                )

            scdr_match = timing_match

            if closest_idx != -1 and timing_match:
                used_pred.add(closest_idx)

            error_type = "NONE (TP)"
            if not timing_match:
                error_type = (
                    "TIMING_OUTSIDE_TOLERANCE (FN)"
                    if closest_pred
                    else "MISSED_TRANSITION (FN)"
                )
            elif not id_match:
                error_type = "WRONG_SPEAKER_IDENTITY (TP timing, wrong ID)"

            sample_name = Path(audio_path).stem
            gt_spk = f"{gt['prev']}->{gt['next']}"
            pr_spk = (
                f"{closest_pred['prev']}->{closest_pred['next']}"
                if closest_pred
                else "N/A"
            )
            pr_time = f"{closest_pred['time']:.2f}" if closest_pred else "N/A"

            print(
                f"| {sample_name} | {gt['time']:.2f} | {gt_spk} | {pr_time} | {pr_spk} | {err_ms:.1f} | {timing_match} | {id_match} | {scdr_match} | {error_type} |"
            )

        for j, p in enumerate(pred_changes):
            if j not in used_pred:
                sample_name = Path(audio_path).stem
                pr_spk = f"{p['prev']}->{p['next']}"
                print(
                    f"| {sample_name} | N/A | N/A | {p['time']:.2f} | {pr_spk} | N/A | False | False | False | EXTRA_FALSE_TRANSITION (FP) |"
                )


if __name__ == "__main__":
    run_ledger()
