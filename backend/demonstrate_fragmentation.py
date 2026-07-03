import subprocess
import warnings

import numpy as np
import torch
from pyannote.audio import Pipeline

from audio.transcriber import get_transcriber
from config.diarization_postprocessing import apply_postprocessing
from services.word_speaker_aligner import align_words_to_speakers

warnings.filterwarnings("ignore")


def decode_audio(path):
    cmd = ["ffmpeg", "-y", "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pcm = proc.stdout.read() # pyright: ignore
    return pcm


def main():
    audio_path = "../sample_audio/meeting_short.mp3"

    pcm = decode_audio(audio_path)

    # 1. Transcribe
    t_whisper = get_transcriber()
    t_whisper.load("tiny", "int8", "cpu")
    raw_segments = t_whisper.transcribe(pcm)

    # 2. Pyannote
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    pipeline.instantiate( # pyright: ignore{"clustering": {"threshold": 0.5}})
    proc = subprocess.run(cmd, capture_output=True, check=True) # pyright: ignore
    assert proc.stdout is not None
    pcm = proc.stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    waveform = {
        "waveform": torch.from_numpy(audio_float32).unsqueeze(0),
        "sample_rate": 16000,
    }

    with torch.inference_mode():
        diarization = pipeline(waveform, num_speakers=2)
    annotation = getattr(diarization, "speaker_diarization", diarization)

    turns = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        mapped = (
            f"Speaker {int(speaker.split('_')[-1]) + 1}"
            if "SPEAKER_" in speaker
            else speaker
        )
        turns.append((turn.start, turn.end, mapped))

    # 3. Emulate post_session_diarizer.py logic
    all_words = []
    for seg in raw_segments:
        if seg.words:
            for w in seg.words:
                all_words.append(
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    }
                )

    aligned_words = align_words_to_speakers(all_words, turns)

    class FakeSeg:
        def __init__(self, start, end, speaker, text):
            self.start = start
            self.end = end
            self.speaker = speaker
            self.text = text
            self.words = []

    new_segments = []
    if aligned_words:
        current_seg_speaker = aligned_words[0]["speaker"]
        current_seg_words = []
        for w in aligned_words:
            if w["speaker"] != current_seg_speaker:
                if current_seg_words:
                    text = "".join(x["word"] for x in current_seg_words).strip()
                    new_segments.append(
                        FakeSeg(
                            current_seg_words[0]["start"],
                            current_seg_words[-1]["end"],
                            current_seg_speaker,
                            text,
                        )
                    )
                current_seg_speaker = w["speaker"]
                current_seg_words = [w]
            else:
                current_seg_words.append(w)
        if current_seg_words:
            text = "".join(x["word"] for x in current_seg_words).strip()
            new_segments.append(
                FakeSeg(
                    current_seg_words[0]["start"],
                    current_seg_words[-1]["end"],
                    current_seg_speaker,
                    text,
                )
            )

    print("BEFORE POST-PROCESSING (RAW RECONSTRUCTION):")
    for s in new_segments:
        print(f"[{s.start:.2f} - {s.end:.2f}] {s.speaker}: {s.text}")

    print("\nAFTER POST-PROCESSING:")
    processed = apply_postprocessing(new_segments)
    for s in processed:
        print(f"[{s.start:.2f} - {s.end:.2f}] {s.speaker}: {s.text}")


if __name__ == "__main__":
    main()
