"""
TalkSense AI -- Clustering Threshold Sweep

Tests internal Pyannote clustering thresholds to find optimal speaker separation.
"""
import json
import os
import subprocess
import sys
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SAMPLE_RATE = 16000
GT_PATH = os.path.join(os.path.dirname(__file__), "backend", "ground_truth", "meeting_short_gt.json")
AUDIO_PATH = os.path.join(os.path.dirname(__file__), "sample_audio", "meeting_short.mp3")


def decode_audio(audio_path):
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pcm = proc.stdout.read()
    proc.wait()
    return pcm


def main():
    from backend.core.config import get_settings
    from backend.audio.transcriber import get_transcriber
    from backend.evaluate_speaker_accuracy import (
        load_ground_truth, Segment as EvalSegment,
        match_segments, resolve_label_mapping,
        compute_accuracy, compute_precision_recall_f1, compute_scdr,
    )
    import torch
    import warnings

    settings = get_settings()

    print("Loading Whisper...")
    transcriber = get_transcriber()
    transcriber.load(settings.whisper_model, settings.whisper_compute_type, settings.whisper_device)

    print("Loading Pyannote...")
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*torchcodec.*", category=UserWarning)
        from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=settings.hf_token)
    pipeline.to(torch.device(settings.pyannote_device))

    print("Decoding audio...")
    pcm_data = decode_audio(AUDIO_PATH)

    print("Loading ground truth...")
    annotated_segs, metadata = load_gt_raw(GT_PATH)

    # Transcribe once (same for all configs)
    print("Transcribing full audio (single pass)...")
    raw_segments = transcriber.transcribe(pcm_data, time_offset=0.0)
    print(f"  Whisper: {len(raw_segments)} segments")

    # Inspect pipeline internals
    print("\n--- Pipeline internal parameters ---")
    try:
        params = pipeline.parameters(instantiated=True)
        print(f"  Keys: {list(params.keys())}")
        if "clustering" in params:
            clustering = params["clustering"]
            print(f"  clustering keys: {list(clustering.keys()) if isinstance(clustering, dict) else clustering}")
        if "segmentation" in params:
            seg_params = params["segmentation"]
            print(f"  segmentation keys: {list(seg_params.keys()) if isinstance(seg_params, dict) else seg_params}")
    except Exception as e:
        print(f"  Could not inspect: {e}")

    # Try to access and modify clustering threshold
    print("\n--- Clustering Threshold Sweep ---")

    # Check what the default threshold is
    default_threshold = None
    try:
        if hasattr(pipeline, '_segmentation'):
            print(f"  _segmentation: {pipeline._segmentation}")
        if hasattr(pipeline, 'clustering'):
            print(f"  clustering: {pipeline.clustering}")

        # Pyannote 3.1 uses YAML-configured pipeline
        # The clustering threshold controls agglomerative clustering merging
        hp = pipeline.parameters(instantiated=True)
        if "clustering" in hp:
            cl = hp["clustering"]
            if isinstance(cl, dict) and "threshold" in cl:
                default_threshold = cl["threshold"]
                print(f"  Default clustering threshold: {default_threshold}")
            else:
                print(f"  Clustering params: {cl}")
    except Exception as e:
        print(f"  Error reading threshold: {e}")

    # Prepare waveform once
    audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
    waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

    # Test a range of clustering thresholds by modifying pipeline params
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    results = []

    for threshold in thresholds:
        print(f"\n  Testing threshold={threshold}...")
        try:
            # Modify the clustering threshold
            hp = pipeline.parameters(instantiated=True)
            if "clustering" in hp and isinstance(hp["clustering"], dict):
                hp["clustering"]["threshold"] = threshold
                pipeline.instantiate(hp)
            else:
                print(f"    Cannot modify clustering threshold, skipping")
                break

            t0 = time.monotonic()
            diarization = pipeline(waveform, num_speakers=2)
            elapsed = time.monotonic() - t0

            # Unwrap
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
                turns.append((turn.start, turn.end, mapped))

            # Assign speakers
            predicted = []
            for seg in raw_segments:
                best_speaker, best_overlap = "Speaker 1", 0.0
                for t_s, t_e, spk in turns:
                    ov = min(seg.end, t_e) - max(seg.start, t_s)
                    if ov > best_overlap:
                        best_overlap = ov
                        best_speaker = spk
                predicted.append(EvalSegment(start=seg.start, end=seg.end, speaker=best_speaker, text=seg.text))

            # Evaluate
            pairs = match_segments(predicted, annotated_segs, min_overlap_ratio=0.10)
            if pairs:
                label_map = resolve_label_mapping(pairs)
                accuracy, correct, total = compute_accuracy(pairs, label_map)
                per_speaker = compute_precision_recall_f1(pairs, label_map)
                scdr, scdr_det, scdr_total = compute_scdr(predicted, annotated_segs, label_map)
                macro_f1 = sum(v["f1"] for v in per_speaker.values()) / len(per_speaker) if per_speaker else 0.0
                speakers = len(set(s.speaker for s in predicted))
            else:
                accuracy, macro_f1, scdr, speakers = 0, 0, 0, 0

            r = {
                "threshold": threshold,
                "speakers": speakers,
                "turns": len(turns),
                "f1": round(macro_f1, 4),
                "scdr": round(scdr, 1),
                "accuracy": round(accuracy, 1),
                "time": round(elapsed, 2),
            }
            results.append(r)
            print(f"    Speakers={speakers} Turns={len(turns)} F1={macro_f1:.4f} SCDR={scdr:.1f}% Acc={accuracy:.1f}% Time={elapsed:.2f}s")

        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"threshold": threshold, "error": str(e)})

    # Restore default
    if default_threshold is not None:
        try:
            hp = pipeline.parameters(instantiated=True)
            hp["clustering"]["threshold"] = default_threshold
            pipeline.instantiate(hp)
        except Exception:
            pass

    # Also test WITHOUT num_speakers constraint at various thresholds
    print("\n--- Threshold sweep WITHOUT num_speakers constraint ---")
    for threshold in [0.4, 0.5, 0.6, 0.7, 0.8]:
        try:
            hp = pipeline.parameters(instantiated=True)
            if "clustering" in hp and isinstance(hp["clustering"], dict):
                hp["clustering"]["threshold"] = threshold
                pipeline.instantiate(hp)
            else:
                break

            t0 = time.monotonic()
            diarization = pipeline(waveform)  # no num_speakers!
            elapsed = time.monotonic() - t0

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
                turns.append((turn.start, turn.end, mapped))

            predicted = []
            for seg in raw_segments:
                best_speaker, best_overlap = "Speaker 1", 0.0
                for t_s, t_e, spk in turns:
                    ov = min(seg.end, t_e) - max(seg.start, t_s)
                    if ov > best_overlap:
                        best_overlap = ov
                        best_speaker = spk
                predicted.append(EvalSegment(start=seg.start, end=seg.end, speaker=best_speaker, text=seg.text))

            pairs = match_segments(predicted, annotated_segs, min_overlap_ratio=0.10)
            if pairs:
                label_map = resolve_label_mapping(pairs)
                accuracy, correct, total = compute_accuracy(pairs, label_map)
                per_speaker = compute_precision_recall_f1(pairs, label_map)
                scdr, scdr_det, scdr_total = compute_scdr(predicted, annotated_segs, label_map)
                macro_f1 = sum(v["f1"] for v in per_speaker.values()) / len(per_speaker) if per_speaker else 0.0
                speakers = len(set(s.speaker for s in predicted))
            else:
                accuracy, macro_f1, scdr, speakers = 0, 0, 0, 0

            print(f"  threshold={threshold} (no constraint): Spk={speakers} F1={macro_f1:.4f} SCDR={scdr:.1f}% Acc={accuracy:.1f}%")
            results.append({
                "threshold": threshold, "constraint": "none",
                "speakers": speakers, "turns": len(turns),
                "f1": round(macro_f1, 4), "scdr": round(scdr, 1),
                "accuracy": round(accuracy, 1), "time": round(elapsed, 2),
            })
        except Exception as e:
            print(f"  threshold={threshold} ERROR: {e}")

    # Save all results
    out_path = os.path.join(os.path.dirname(__file__), "backend", "threshold_sweep_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


def load_gt_raw(path):
    from backend.evaluate_speaker_accuracy import load_ground_truth
    return load_ground_truth(path)


if __name__ == "__main__":
    main()
