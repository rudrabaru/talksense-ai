import whisper

# Load model once (important for performance)
model = whisper.load_model("base")  # base = balance of speed + accuracy

def transcribe_audio(file_path: str):
    """
    Transcribes audio file into text segments.
    """
    result = model.transcribe(file_path)

    segments = []
    for segment in result["segments"]:
        segments.append({
            "start": round(segment["start"], 2),
            "end": round(segment["end"], 2),
            "text": segment["text"].strip()
        })

    return {
        "text": result["text"].strip(),
        "segments": segments
    }
