from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil
import sys

# Add the current directory to sys.path to allow imports of 'services'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.speech_to_text import transcribe_audio
from services.nlp_engine import NLPEngine
from services.context_analyzer import analyze_meeting, analyze_sales

app = FastAPI(
    title="TalkSense AI",
    description="AI Conversation Intelligence Platform",
    version="1.0"
)

nlp_engine = NLPEngine()

UPLOAD_DIR = "uploads"

@app.get("/health")
def health_check():
    return {"status": "TalkSense AI backend running"}

@app.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    mode: str = "meeting"  # "meeting" or "sales"
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Speech-to-Text
    raw_transcript_data = transcribe_audio(file_path)
    # Extract just the segments list (assuming transcribe_audio returns a dict with "segments")
    raw_segments = raw_transcript_data.get("segments", [])

    # 2. NLP Enrichment (Sentiment + Keywords)
    # Use the instance nlp_engine to enrich
    enriched_segments = nlp_engine.enrich_transcript(raw_segments)

    # 3. Context Analysis
    # 3. Context Analysis
    # Prepare data structure expected by analyzers and frontend
    final_transcript = {
        "text": raw_transcript_data.get("text", ""),
        "segments": enriched_segments
    }

    insights = {}
    if mode == "sales":
        # Note: analyze_sales might need adaptation if it expects a dict with "segments" key
        # For now, we reconstruct the input it expects if needed, or update analyze_sales.
        # Current analyze_sales expects a dict with "segments" key.
        insights = analyze_sales({"segments": enriched_segments})
    else:
        # Default to meeting mode
        insights = analyze_meeting(final_transcript)

    # 4. Construct Final Response
    return JSONResponse(
        content={
            "filename": file.filename,
            "mode": mode,
            "transcript": enriched_data, # Use the enriched version with sentiment
            "insights": insights
        }
    )
