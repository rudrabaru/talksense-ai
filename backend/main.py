from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil

from services.speech_to_text import transcribe_audio

app = FastAPI(
    title="TalkSense AI",
    description="AI Conversation Intelligence Platform",
    version="1.0"
)

UPLOAD_DIR = "uploads"

@app.get("/health")
def health_check():
    return {"status": "TalkSense AI backend running"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Speech-to-text
    transcript = transcribe_audio(file_path)

    return JSONResponse(
        content={
            "filename": file.filename,
            "transcript": transcript
        }
    )
