"""
TalkSense AI — Benchmark Dataset Ground Truth Generator

Transcribes + diarizes all sample audio files to produce draft
ground truth annotations for manual review.

Outputs a JSON per file with Whisper segments + Pyannote speaker labels.
"""
import json
import os
import subprocess
import sys
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

SAMPLE_RATE = 16000
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "sample_audio")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "backend", "benchmark_dataset", "_drafts")


def decode_audio(path):
    cmd = ["ffmpeg", "-y", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pcm = proc.stdout.read()
    proc.wait()
    return pcm


def main():
    from backend.core.config import get_settings
    from backend.audio.transcriber import get_transcriber
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

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    audio_files = sorted([
        f for f in os.listdir(AUDIO_DIR)
        if f.endswith((".mp3", ".m4a", ".wav"))
    ])

    for i, fname in enumerate(audio_files):
        audio_path = os.path.join(AUDIO_DIR, fname)
        print(f"\n[{i+1}/{len(audio_files)}] Processing: {fname}")

        # Decode
        pcm = decode_audio(audio_path)
        duration = len(pcm) / 2 / SAMPLE_RATE
        print(f"  Duration: {duration:.1f}s  PCM: {len(pcm)} bytes")

        # Transcribe
        t0 = time.monotonic()
        segments = transcriber.transcribe(pcm, time_offset=0.0)
        t_whisper = time.monotonic() - t0
        print(f"  Whisper: {len(segments)} segments in {t_whisper:.1f}s")

        # Diarize (full audio, no speaker hint)
        audio_int16 = np.frombuffer(pcm, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)
        waveform = {"waveform": audio_tensor, "sample_rate": SAMPLE_RATE}

        t0 = time.monotonic()
        diarization = pipeline(waveform)
        t_pyannote = time.monotonic() - t0

        # Unwrap
        try:
            from pyannote.audio.pipelines.speaker_diarization import DiarizeOutput
            if isinstance(diarization, DiarizeOutput):
                annotation = diarization.speaker_diarization
            else:
                annotation = diarization
        except ImportError:
            annotation = diarization

        # Build turns
        turns = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            mapped = speaker
            if speaker.startswith("SPEAKER_"):
                try:
                    num = int(speaker.split("_")[-1])
                    mapped = f"Speaker {num + 1}"
                except (ValueError, IndexError):
                    pass
            turns.append({"start": round(turn.start, 2), "end": round(turn.end, 2), "speaker": mapped})

        unique_speakers = list(set(t["speaker"] for t in turns))
        print(f"  Pyannote: {len(turns)} turns, {len(unique_speakers)} speakers in {t_pyannote:.1f}s")

        # Assign speakers to segments
        seg_data = []
        for seg in segments:
            best_speaker, best_ov = "Unknown", 0.0
            for t in turns:
                ov = min(seg.end, t["end"]) - max(seg.start, t["start"])
                if ov > best_ov:
                    best_ov = ov
                    best_speaker = t["speaker"]
            seg_data.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "speaker": best_speaker,
                "text": seg.text.strip(),
            })

        # Build output
        stem = os.path.splitext(fname)[0]
        result = {
            "recording": fname,
            "duration_seconds": round(duration, 1),
            "speakers_detected": len(unique_speakers),
            "speaker_labels": sorted(unique_speakers),
            "whisper_time_s": round(t_whisper, 1),
            "pyannote_time_s": round(t_pyannote, 1),
            "segments": seg_data,
            "pyannote_turns": turns,
        }

        out_path = os.path.join(OUTPUT_DIR, f"{stem}_draft.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  Saved: {out_path}")

    print(f"\n{'='*60}")
    print(f"  All {len(audio_files)} files processed. Drafts in: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
