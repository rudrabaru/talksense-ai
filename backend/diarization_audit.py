"""
TalkSense AI — Diarization Reality Audit Script

Runs TWO independent diarization paths on the same audio file and compares:

  Path A: LIVE chunked diarization (5s chunks → Pyannote per chunk)
  Path B: POST-SESSION full-WAV diarization (single Pyannote pass on entire file)

Then evaluates both against the ground truth to produce measured metrics.
"""

import json
import os
import subprocess
import sys
import time
import wave

import numpy as np

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio.diarizer import get_diarizer
from audio.transcriber import get_transcriber
from core.config import get_settings
from evaluate_speaker_accuracy import Segment as EvalSegment
from evaluate_speaker_accuracy import (
    collect_failures,
    compute_accuracy,
    compute_precision_recall_f1,
    compute_scdr,
    load_ground_truth,
    match_segments,
    resolve_label_mapping,
)

SAMPLE_RATE = 16000
CHUNK_DURATION_SECS = 5.0
CHUNK_SIZE_BYTES = int(SAMPLE_RATE * 2 * CHUNK_DURATION_SECS)

GT_PATH = os.path.join(
    os.path.dirname(__file__), "ground_truth", "meeting_short_gt.json"
)
AUDIO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "sample_audio", "meeting_short.mp3")
)


def decode_audio_to_pcm(audio_path: str) -> bytes:
    """Decode audio file to raw PCM using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    pcm_data = proc.stdout.read()
    proc.wait()
    return pcm_data


def write_pcm_to_wav(pcm_bytes: bytes, wav_path: str) -> None:
    """Write raw PCM bytes to a valid WAV file for Pyannote."""
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)


def evaluate_segments(predicted_segs, annotated_segs):
    """Run the full evaluation pipeline and return a metrics dict."""
    pairs = match_segments(predicted_segs, annotated_segs, min_overlap_ratio=0.10)

    if not pairs:
        return {
            "segments_matched": 0,
            "total_annotated": len(annotated_segs),
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "scdr": 0.0,
            "per_speaker": {},
            "label_map": {},
            "failures": [],
        }

    label_map = resolve_label_mapping(pairs)
    accuracy, correct, total_matched = compute_accuracy(pairs, label_map)
    per_speaker = compute_precision_recall_f1(pairs, label_map)
    scdr, scdr_detected, scdr_total, _, _ = compute_scdr(
        predicted_segs, annotated_segs, label_map
    )
    macro_f1 = (
        sum(v["f1"] for v in per_speaker.values()) / len(per_speaker)
        if per_speaker
        else 0.0
    )
    failures = collect_failures(pairs, label_map)

    return {
        "segments_matched": len(pairs),
        "total_annotated": len(annotated_segs),
        "accuracy": round(accuracy, 1),
        "correct": correct,
        "total_matched": total_matched,
        "macro_f1": round(macro_f1, 3),
        "scdr": round(scdr, 1),
        "scdr_detected": scdr_detected,
        "scdr_total": scdr_total,
        "per_speaker": per_speaker,
        "label_map": {k: v for k, v in label_map.items()},
        "failures": failures,
    }


# ── PATH A: Live Chunked Diarization ─────────────────────────────────────────


def run_live_chunked(pcm_data: bytes, transcriber, diarizer) -> list[EvalSegment]:
    """Simulate the WebSocket pipeline: chunk → transcribe → diarize per chunk."""
    print("\n" + "=" * 60)
    print("  PATH A: LIVE CHUNKED DIARIZATION (5s chunks)")
    print("=" * 60)

    all_segments = []
    offset_bytes = 0
    time_offset = 0.0
    prev_speaker = "Speaker 1"

    from audio.speaker_profile import SpeakerProfile

    speaker_profile = SpeakerProfile()

    while offset_bytes < len(pcm_data):
        chunk = pcm_data[offset_bytes : offset_bytes + CHUNK_SIZE_BYTES]
        chunk_duration = (len(chunk) / 2) / SAMPLE_RATE

        raw_segments = transcriber.transcribe(chunk, time_offset=time_offset)

        if raw_segments:
            diarized = diarizer.assign_speakers(
                raw_segments, chunk, time_offset, prev_speaker, speaker_profile
            )
            if diarized:
                prev_speaker = diarized[-1].speaker
                for seg in diarized:
                    all_segments.append(
                        EvalSegment(
                            start=seg.start,
                            end=seg.end,
                            speaker=seg.speaker,
                            text=seg.text,
                        )
                    )
                    print(
                        f"  [{seg.start:6.2f} - {seg.end:6.2f}] {seg.speaker:12s}: {seg.text[:60]}"  # noqa: E501
                    )

        offset_bytes += len(chunk)
        time_offset += chunk_duration

    print(f"\n  Total segments: {len(all_segments)}")
    speakers = set(s.speaker for s in all_segments)
    print(f"  Unique speakers detected: {len(speakers)} -> {speakers}")
    return all_segments


# ── PATH B: Post-Session Full-WAV Diarization ────────────────────────────────


def run_post_session(pcm_data: bytes, transcriber, diarizer) -> list[EvalSegment]:
    """Simulate the post-session pipeline: full WAV → single Pyannote pass."""
    print("\n" + "=" * 60)
    print("  PATH B: POST-SESSION FULL-WAV DIARIZATION")
    print("=" * 60)

    # Step 1: Transcribe the ENTIRE audio in one shot (same as live but one chunk)
    print("  Transcribing full audio...")
    raw_segments = transcriber.transcribe(pcm_data, time_offset=0.0)
    print(f"  Whisper returned {len(raw_segments)} segment(s)")

    if not raw_segments:
        print("  ERROR: No segments from Whisper")
        return []

    # Step 2: Run Pyannote on the FULL audio (like post_session_diarizer.py)
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*torchcodec.*", category=UserWarning
            )
            from pyannote.audio import Pipeline
        import torch

        settings = get_settings()
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=settings.hf_token,
        )
        assert pipeline is not None
        pipeline.to(torch.device(settings.pyannote_device))
    except Exception as e:
        print(f"  ERROR: Failed to load Pyannote directly: {e}")
        return []

    import torch

    audio_int16 = np.frombuffer(pcm_data, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
    waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

    print("  Running Pyannote on full waveform...")
    t0 = time.monotonic()
    diarization = pipeline(waveform, num_speakers=2)
    elapsed = time.monotonic() - t0
    print(f"  Pyannote finished in {elapsed:.1f}s")

    # Unwrap DiarizeOutput wrapper if present (pyannote-audio 4.x) using duck-typing
    # to bypass class-identity mismatches under Uvicorn reload environments.
    annotation = getattr(diarization, "speaker_diarization", diarization)

    # Build turn timeline
    turns = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):  # type: ignore
        mapped = speaker
        if speaker.startswith("SPEAKER_"):
            try:
                num = int(speaker.split("_")[-1])
                mapped = f"Speaker {num + 1}"
            except (ValueError, IndexError):
                pass
        turns.append((turn.start, turn.end, mapped))

    print(f"  Pyannote turns: {len(turns)}")
    for t_start, t_end, spk in turns:
        print(f"    [{t_start:6.2f} - {t_end:6.2f}] {spk}")

    unique_speakers = set(s for _, _, s in turns)
    print(f"  Unique speakers: {len(unique_speakers)} -> {unique_speakers}")

    # Step 3: Assign speakers to Whisper segments using overlap (same as
    # post_session_diarizer)
    all_segments = []
    for seg in raw_segments:
        best_speaker = "Speaker 1"
        best_overlap = 0.0
        for t_start, t_end, spk in turns:
            overlap = min(seg.end, t_end) - max(seg.start, t_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = spk
        all_segments.append(
            EvalSegment(
                start=seg.start,
                end=seg.end,
                speaker=best_speaker,
                text=seg.text,
            )
        )
        print(
            f"  [{seg.start:6.2f} - {seg.end:6.2f}] {best_speaker:12s}: {seg.text[:60]}"
        )

    print(f"\n  Total segments: {len(all_segments)}")
    return all_segments


# ── MAIN ─────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  TALKSENSE AI — DIARIZATION REALITY AUDIT")
    print("=" * 60)

    settings = get_settings()

    # Load models
    print("\n[1/4] Loading Whisper...")
    transcriber = get_transcriber()
    transcriber.load(
        settings.whisper_model, settings.whisper_compute_type, settings.whisper_device
    )

    print("[2/4] Loading Pyannote...")
    diarizer = get_diarizer()
    diarizer.load(settings.hf_token, settings.pyannote_device)

    print("[3/4] Decoding audio...")
    pcm_data = decode_audio_to_pcm(AUDIO_PATH)
    print(f"  PCM size: {len(pcm_data)} bytes ({len(pcm_data) / 2 / SAMPLE_RATE:.1f}s)")

    print("[4/4] Loading ground truth...")
    annotated_segs, metadata = load_ground_truth(GT_PATH)
    print(
        f"  Ground truth: {len(annotated_segs)} segments, {metadata['expected_speakers']} speakers"  # noqa: E501
    )

    # ── Run Path A ────────────────────────────────────────────────────────────
    live_segments = run_live_chunked(pcm_data, transcriber, diarizer)
    live_metrics = evaluate_segments(live_segments, annotated_segs)

    # ── Run Path B ────────────────────────────────────────────────────────────
    post_segments = run_post_session(pcm_data, transcriber, diarizer)
    post_metrics = evaluate_segments(post_segments, annotated_segs)

    # ── Print comparison ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  COMPARISON: LIVE vs POST-SESSION")
    print("=" * 60)

    headers = f"{'Metric':<30} {'LIVE (chunked)':<20} {'POST-SESSION (full)':<20}"
    print(headers)
    print("-" * 70)

    rows = [
        (
            "Segments Matched",
            f"{live_metrics['segments_matched']}/{live_metrics['total_annotated']}",
            f"{post_metrics['segments_matched']}/{post_metrics['total_annotated']}",
        ),
        (
            "Attribution Accuracy",
            f"{live_metrics['accuracy']}%",
            f"{post_metrics['accuracy']}%",
        ),
        ("Macro F1", f"{live_metrics['macro_f1']}", f"{post_metrics['macro_f1']}"),
        ("SCDR", f"{live_metrics['scdr']}%", f"{post_metrics['scdr']}%"),
    ]
    for label, live_val, post_val in rows:
        print(f"  {label:<28} {live_val:<20} {post_val:<20}")

    print("\n  Label Mappings:")
    print(f"    LIVE:         {live_metrics.get('label_map', {})}")
    print(f"    POST-SESSION: {post_metrics.get('label_map', {})}")

    # ── Save results ──────────────────────────────────────────────────────────
    results = {
        "audio_file": AUDIO_PATH,
        "ground_truth": GT_PATH,
        "live_chunked": live_metrics,
        "post_session": post_metrics,
    }

    output_path = os.path.join(
        os.path.dirname(__file__), "diarization_audit_results.json"
    )
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if post_metrics["macro_f1"] >= 0.75 and post_metrics["scdr"] >= 70.0:
        print("  POST-SESSION VERDICT: [PASS]")
    else:
        print("  POST-SESSION VERDICT: [FAIL]")

    if live_metrics["macro_f1"] >= 0.75 and live_metrics["scdr"] >= 70.0:
        print("  LIVE VERDICT:         [PASS]")
    else:
        print("  LIVE VERDICT:         [FAIL]")
    print("=" * 60)


if __name__ == "__main__":
    main()
