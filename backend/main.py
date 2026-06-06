# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, Form, WebSocket
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

# pyrefly: ignore [missing-import]
from starlette.concurrency import run_in_threadpool
import os
import shutil
import sys
import asyncio

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

# Enable CORS for Frontend
# NOTE: allow_origins=["*"] is used for hackathon/demo purposes.
# For production, restrict to specific domains: allow_origins=["https://yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for hackathon/demo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp_engine = NLPEngine()

UPLOAD_DIR = "uploads"

@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Status message indicating backend is running
    """
    return {"status": "TalkSense AI backend running"}

@app.websocket("/ws/transcript")
async def websocket_transcript(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming.

    Day 1: Sends initial greeting messages (Hello, World, Testing).
    Day 3: Receives binary audio chunks from the browser, logs their size,
           and sends back chunk_ack acknowledgments.

    Flow: Browser 🎙 → WebSocket 📡 → FastAPI 🖥
    """
    await websocket.accept()
    print("Client connected")

    try:
        # Day 1: Send initial greeting messages
        messages = ["Hello", "World", "Testing"]
        for msg in messages:
            await websocket.send_json({"text": msg})
            await asyncio.sleep(1)

        # Day 3: Receive binary audio chunks continuously
        chunk_count = 0
        total_bytes = 0
        while True:
            audio_chunk = await websocket.receive_bytes()
            chunk_count += 1
            total_bytes += len(audio_chunk)

            print(
                f"Received chunk #{chunk_count}: "
                f"{len(audio_chunk)} bytes "
                f"(total: {total_bytes / 1024:.1f} KB)"
            )

            # Send acknowledgment back to frontend
            await websocket.send_json({
                "type": "chunk_ack",
                "chunk": chunk_count,
                "size": len(audio_chunk),
            })

    except Exception as e:
        print(f"Disconnected: {e}")
        print(f"Session summary: {chunk_count} chunks, {total_bytes / 1024:.1f} KB total")

@app.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    mode: str = Form("meeting")  # Explicitly mark as Form field
):
    """
    Main analysis endpoint for processing audio files.
    
    Processes audio through 3-stage pipeline:
    1. Speech-to-Text (Whisper transcription)
    2. NLP Enrichment (Sentiment + keyword extraction)
    3. Context Analysis (Mode-specific insights)
    
    Args:
        file: Audio file upload (mp3, wav, m4a)
        mode: Analysis mode - "meeting" or "sales" (default: "meeting")
    
    Returns:
        JSONResponse: Structured analysis results including transcript and insights
    
    Raises:
        HTTPException: If file processing fails or invalid mode provided
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    def save_upload(input_file, output_path):
        """Helper function to save uploaded file to disk."""
        with open(output_path, "wb") as buffer:
            shutil.copyfileobj(input_file, buffer)

    try:
        await run_in_threadpool(save_upload, file.file, file_path)

        # 1. Speech-to-Text (Blocking -> ThreadPool)
        # Whisper releases GIL, so threads are effective
        raw_transcript_data = await run_in_threadpool(transcribe_audio, file_path)
        # Extract just the segments list (assuming transcribe_audio returns a dict with "segments")
        raw_segments = raw_transcript_data.get("segments", [])

        # 2. NLP Enrichment (Sentiment + Keywords) (Blocking -> ThreadPool)
        # Transformers pipeline also releases GIL
        enriched_segments = await run_in_threadpool(nlp_engine.enrich_transcript, raw_segments)

        # 3. Context Analysis
        # Prepare data structure expected by analyzers and frontend
        final_transcript = {
            "text": raw_transcript_data.get("text", ""),
            "segments": enriched_segments
        }

        insights = {}
        if mode == "sales":
            # analyze_sales expects a list of segments
            insights = await run_in_threadpool(analyze_sales, enriched_segments)
        else:
            # Default to meeting mode
            insights = await run_in_threadpool(analyze_meeting, final_transcript)

        # 4. Construct Final Response
        return JSONResponse(
            content={
                "filename": file.filename,
                "mode": mode,
                "transcript": final_transcript,  # Use the enriched version with sentiment
                "insights": insights
            }
        )
    
    finally:
        # Clean up uploaded file to prevent disk space accumulation
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                # Log error in production, but don't fail the response
                pass

