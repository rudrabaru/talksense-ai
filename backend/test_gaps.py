import subprocess

from audio.transcriber import get_transcriber


def main():
    transcriber = get_transcriber()
    transcriber.load("tiny", "int8", "cpu")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        "../sample_audio/sales_good.mp3",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    assert proc.stdout is not None
    pcm = proc.stdout
    segments = transcriber.transcribe(pcm)
    print("WITH WORD TIMESTAMPS:")
    for s in segments:
        print(f"[{s.start:.2f} - {s.end:.2f}] {s.text}")


if __name__ == "__main__":
    main()
