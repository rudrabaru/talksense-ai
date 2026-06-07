"""
TalkSense AI v4 — FastAPI Application Entry Point

Startup sequence:
  1. Load environment config
  2. Connect to PostgreSQL
  3. Warm up AI models (VAD, Whisper, Pyannote, Sentiment)
  4. Register routers

WebSocket endpoints:
  /ws/audio/{session_id}      ← receives binary PCM audio
  /ws/transcript/{session_id} ← pushes live transcript
  /ws/metrics/{session_id}    ← pushes live metrics
  /ws/alerts/{session_id}     ← pushes real-time alerts
  /ws/status/{session_id}     ← pushes session state changes

REST endpoints:
  POST   /sessions
  GET    /sessions/{id}
  DELETE /sessions/{id}
  POST   /clients
  GET    /clients
  GET    /clients/{id}
  GET    /reports/{session_id}
  GET    /dashboard/{session_id}
  POST   /auth/register
  POST   /auth/login
  GET    /auth/me
  POST   /analyze           ← legacy batch mode (kept for compatibility)
  GET    /health
"""
import logging
import os
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Config ────────────────────────────────────────────────────────────────────
from core.config import get_settings

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("talksense")


# ── Lifespan: startup + shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise all AI models and DB on startup.
    Runs once before the first request is served.
    """
    logger.info("=" * 60)
    logger.info("TalkSense AI v4 — Starting up")
    logger.info("=" * 60)

    # 1. VAD (CPU, fast)
    logger.info("Loading Silero VAD …")
    from audio.vad import get_vad
    get_vad()  # loads and caches singleton

    # 2. Faster Whisper (GPU)
    logger.info(
        f"Loading Whisper ({settings.whisper_model}, "
        f"{settings.whisper_compute_type}, {settings.whisper_device}) …"
    )
    from audio.transcriber import get_transcriber
    transcriber = get_transcriber()
    transcriber.load(
        model_name=settings.whisper_model,
        compute_type=settings.whisper_compute_type,
        device=settings.whisper_device,
    )

    # 3. Pyannote (GPU, optional)
    if settings.pyannote_enabled and settings.hf_token:
        logger.info("Loading Pyannote speaker diarization …")
        from audio.diarizer import get_diarizer
        diarizer = get_diarizer()
        diarizer.load(hf_token=settings.hf_token, device=settings.pyannote_device)
    else:
        logger.info("Pyannote: disabled or no HF_TOKEN — using heuristic speaker assignment")

    # 4. Sentiment model (CPU/GPU — Transformers)
    logger.info("Loading sentiment model …")
    from services.nlp_engine import NLPEngine
    NLPEngine()  # loads and warms up transformers pipeline

    logger.info("=" * 60)
    logger.info("All models loaded. TalkSense AI is ready.")
    logger.info("=" * 60)

    yield  # ── App is running ──────────────────────────────────────────────

    logger.info("TalkSense AI — Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TalkSense AI",
    description="AI-Powered Conversation Intelligence Platform",
    version="4.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket routers ─────────────────────────────────────────────────────────
from ws.audio_handler import router as audio_router
from ws.subscriptions import router as subscriptions_router

app.include_router(audio_router)
app.include_router(subscriptions_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "ok",
        "service": "TalkSense AI",
        "version": "4.0.0",
    }


# ── Session REST endpoints ────────────────────────────────────────────────────
@app.post("/sessions", tags=["Sessions"])
async def create_session(
    mode: str = "meeting",
    client_id: str | None = None,
):
    """
    Create a new session.

    Returns the session_id needed to connect the WebSocket channels.
    """
    from ws.session_manager import get_session_manager

    manager = get_session_manager()
    session = manager.create(mode=mode, client_id=client_id)

    return {
        "session_id": session.session_id,
        "mode": session.mode,
        "status": session.status,
        "ws": {
            "audio":      f"/ws/audio/{session.session_id}",
            "transcript": f"/ws/transcript/{session.session_id}",
            "metrics":    f"/ws/metrics/{session.session_id}",
            "alerts":     f"/ws/alerts/{session.session_id}",
            "status":     f"/ws/status/{session.session_id}",
        },
    }


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str):
    """Get current state of an active session."""
    from ws.session_manager import get_session_manager

    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    return {
        "session_id": session.session_id,
        "mode": session.mode,
        "status": session.status,
        "elapsed_seconds": round(session.elapsed_seconds, 1),
        "health_score": session.conversation.health_score,
        "sentiment": session.conversation.sentiment,
    }


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def end_session(session_id: str):
    """Gracefully end an active session."""
    from ws.session_manager import get_session_manager, SessionStatus

    manager = get_session_manager()
    await manager.end(session_id, SessionStatus.COMPLETED)
    return {"session_id": session_id, "status": "completed"}


# ── Dashboard snapshot ────────────────────────────────────────────────────────
@app.get("/dashboard/{session_id}", tags=["Dashboard"])
async def get_dashboard_snapshot(session_id: str):
    """
    Get the current full conversation state for a session.
    Used on reconnect to restore dashboard state.
    """
    from ws.session_manager import get_session_manager

    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    conv = session.conversation
    return {
        "session_id": session_id,
        "mode": session.mode,
        "status": session.status,
        "elapsed_seconds": round(session.elapsed_seconds, 1),
        "health_score": conv.health_score,
        "sentiment": conv.sentiment,
        "sentiment_score": conv.sentiment_score,
        "speaking_ratio": conv.speaking_ratio,
        "participation": conv.participation,
        "filler_count": conv.filler_count,
        "objections": conv.objections,
        "buying_signals": conv.buying_signals,
        "active_alerts": conv.active_alerts,
        "transcript_segments": conv.transcript_segments[-50:],  # last 50 segments
    }


# ── Legacy batch analysis endpoint (kept for compatibility) ───────────────────
@app.post("/analyze", tags=["Legacy"])
async def analyze_audio(
    file: UploadFile = File(...),
    mode: str = Form("meeting"),
):
    """
    Legacy batch audio analysis endpoint.
    Kept for backward compatibility with the original batch upload flow.
    For real-time analysis, use the WebSocket pipeline.
    """
    import shutil

    from services.nlp_engine import NLPEngine
    from services.context_analyzer import analyze_meeting, analyze_sales

    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    def save_upload(input_file, output_path):
        with open(output_path, "wb") as buffer:
            shutil.copyfileobj(input_file, buffer)

    try:
        await run_in_threadpool(save_upload, file.file, file_path)

        # Use legacy openai-whisper transcriber (services/speech_to_text.py)
        from services.speech_to_text import transcribe_audio
        raw_transcript_data = await run_in_threadpool(transcribe_audio, file_path)
        raw_segments = raw_transcript_data.get("segments", [])

        nlp = NLPEngine()
        enriched_segments = await run_in_threadpool(nlp.enrich_transcript, raw_segments)

        final_transcript = {
            "text": raw_transcript_data.get("text", ""),
            "segments": enriched_segments,
        }

        if mode == "sales":
            insights = await run_in_threadpool(analyze_sales, enriched_segments)
        else:
            insights = await run_in_threadpool(analyze_meeting, final_transcript)

        return JSONResponse(content={
            "filename": file.filename,
            "mode": mode,
            "transcript": final_transcript,
            "insights": insights,
        })

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
