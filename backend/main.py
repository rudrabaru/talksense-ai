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
from datetime import datetime

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi import Depends as _Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from starlette.concurrency import run_in_threadpool

from db.database import get_db
from db.database import get_db as _get_db
from ws.audio_handler import router as audio_router
from ws.subscriptions import router as subscriptions_router

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Config ────────────────────────────────────────────────────────────────────
from core.config import get_settings
from utils.profiler import profile_stage

settings = get_settings()
if settings.hf_token:
    os.environ["HF_TOKEN"] = settings.hf_token


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

    try:
        # 0. PostgreSQL — create tables if they do not exist
        logger.info("DB — connecting to PostgreSQL and running create_all() …")
        from db.database import AsyncSessionLocal, create_all

        await create_all()

        # 0b. Startup recovery: bulk-transition orphaned sessions
        logger.info("DB — running startup recovery for stale sessions …")
        from db.crud import recover_stale_sessions

        async with AsyncSessionLocal() as db:
            await recover_stale_sessions(db)

        if settings.env != "test":
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
                diarizer.load(
                    hf_token=settings.hf_token,
                    device=settings.pyannote_device,
                )
            else:
                logger.info(
                    "Pyannote: disabled or no HF_TOKEN — "
                    "using heuristic speaker assignment"
                )

            # 4. Sentiment model (CPU/GPU — Transformers)
            logger.info("Loading sentiment model …")
            from services.nlp_engine import get_nlp_engine

            get_nlp_engine()  # loads and caches the singleton; reused by audio_handler

        # 5. Start background flusher loop
        logger.info("Flusher — starting background flusher scheduler …")
        import inspect
        from typing import Any

        from ws.session_manager import start_flusher

        res: Any = start_flusher()
        if inspect.isawaitable(res):
            await res

        logger.info("=" * 60)
        logger.info(
            "All models loaded. TalkSense AI is ready."
            if settings.env != "test"
            else "TalkSense AI is ready (Test Mode)."
        )
        logger.info("=" * 60)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Application startup failed: %s", exc)
        raise

    yield  # ── App is running ──────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("TalkSense AI — Shutting down")

    try:
        from ws.session_manager import stop_flusher

        await stop_flusher()
        logger.info("Flusher — background flusher stopped.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Flusher — shutdown failed: %s", exc)
    finally:
        from db.database import engine

        await engine.dispose()
        logger.info("DB — connection pool disposed.")


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


@app.get("/check_diarizer", tags=["System"])
def check_diarizer():
    from audio.diarizer import get_diarizer

    diarizer = get_diarizer()
    return {
        "loaded": diarizer._loaded,
        "has_pipeline": diarizer._pipeline is not None,
        "hf_token_len": len(settings.hf_token) if settings.hf_token else 0,
        "pyannote_enabled": settings.pyannote_enabled,
    }


# ── Session REST endpoints ────────────────────────────────────────────────────


class SessionCreateRequest(BaseModel):
    mode: str = "meeting"
    client_id: str | None = None


@app.post("/sessions", tags=["Sessions"])
async def create_session(
    body: SessionCreateRequest = Body(default=None),
    mode: str | None = None,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new session.

    Returns the session_id needed to connect the WebSocket channels.
    """
    from db import crud
    from ws.session_manager import get_session_manager

    # Determine mode and client_id, prioritizing request body
    req_mode = "meeting"
    req_client_id = None

    if body is not None:
        req_mode = body.mode
        req_client_id = body.client_id

        # If body uses defaults, but query parameters specify custom values, use the
        # query parameters
        if req_mode == "meeting" and mode is not None:
            req_mode = mode
        if req_client_id is None and client_id is not None:
            req_client_id = client_id
    else:
        # Fallback to query parameters
        req_mode = mode if mode is not None else "meeting"
        req_client_id = client_id

    manager = get_session_manager()
    session = manager.create(mode=req_mode, client_id=req_client_id)

    # Persist the session to PostgreSQL immediately
    db_session = await crud.create_session(
        db,
        session_id=session.session_id,
        mode=session.mode,
        client_id=req_client_id,
    )
    await db.commit()
    await db.refresh(db_session)

    return {
        "session_id": session.session_id,
        "mode": session.mode,
        "status": session.status,
        "ws": {
            "audio": f"/ws/audio/{session.session_id}",
            "transcript": f"/ws/transcript/{session.session_id}",
            "metrics": f"/ws/metrics/{session.session_id}",
            "alerts": f"/ws/alerts/{session.session_id}",
            "status": f"/ws/status/{session.session_id}",
        },
    }


class SessionSummary(BaseModel):
    session_id: str
    mode: str
    status: str
    title: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration: float | None = None
    client_id: str | None = None
    client_name: str | None = None
    health_score: int | None = None
    sentiment: str | None = None


class PaginatedSessionsResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[SessionSummary]


@app.get("/sessions/compare", tags=["Sessions"])
async def compare_sessions(
    id1: str,
    id2: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two completed sessions side-by-side.

    Query params:
        id1 — UUID of the first session
        id2 — UUID of the second session

    Response 200: ComparisonResult (see services/comparison.py for full schema)
    Response 400: if id1 == id2
    Response 404: if either session is not found in the database
    """
    if id1 == id2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="id1 and id2 must be different sessions.",
        )

    from services.comparison import build_comparison

    try:
        result = await build_comparison(db, id1, id2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error in /sessions/compare: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build session comparison.",
        )

    return JSONResponse(content=result)


@app.get("/sessions", response_model=PaginatedSessionsResponse, tags=["Sessions"])
async def list_historical_sessions(
    mode: str | None = None,
    status: str | None = None,
    client_id: str | None = None,
    search: str | None = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    List historical sessions with search, filters, pagination, and sorting.
    """
    from db import crud

    # Restrict page and limit values to sensible bounds
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    elif limit > 100:
        limit = 100

    items, total = await crud.list_sessions_paginated(
        db,
        mode=mode,
        status=status,
        client_id=client_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
    }


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current state of an active or terminal/persisted session."""
    from db import crud
    from ws.session_manager import get_session_manager

    manager = get_session_manager()
    session = manager.get(session_id)
    if session is not None:
        return {
            "session_id": session.session_id,
            "mode": session.mode,
            "status": session.status,
            "elapsed_seconds": round(session.elapsed_seconds, 1),
            "health_score": session.conversation.health_score,
            "sentiment": session.conversation.sentiment,
        }

    # DB Fallback for inactive/terminal sessions
    db_session = await crud.get_session(db, session_id)
    if db_session is None:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    # Fetch latest metrics to populate contract fields
    metrics_list = await crud.get_latest_session_metrics(db, session_id)
    health_score = 50
    sentiment = "neutral"
    for m in metrics_list:
        if m.metric_name == "health_score" and isinstance(m.metric_value, (int, float)):
            health_score = m.metric_value
        elif m.metric_name == "sentiment" and isinstance(m.metric_value, str):
            sentiment = m.metric_value

    # Compute elapsed seconds
    elapsed = 0.0
    if db_session.duration is not None:
        elapsed = round(db_session.duration, 1)
    elif db_session.ended_at and db_session.started_at:
        diff = (db_session.ended_at - db_session.started_at).total_seconds()
        elapsed = round(max(0.0, diff), 1)

    return {
        "session_id": str(db_session.id),
        "mode": db_session.mode,
        "status": db_session.status,
        "elapsed_seconds": elapsed,
        "health_score": health_score,
        "sentiment": sentiment,
    }


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def end_session(session_id: str):
    """Gracefully end an active session."""
    from ws.session_manager import SessionStatus, get_session_manager

    manager = get_session_manager()
    await manager.end(session_id, SessionStatus.COMPLETED)
    return {"session_id": session_id, "status": "completed"}


# ── Dashboard snapshot ────────────────────────────────────────────────────────


@app.get("/dashboard/{session_id}", tags=["Dashboard"])
async def get_dashboard_snapshot(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current full conversation state for a session.
    Used on reconnect to restore dashboard state.
    """
    from db import crud
    from ws.session_manager import get_session_manager

    manager = get_session_manager()
    session = manager.get(session_id)
    if session is not None:
        conv = session.conversation
        attr_status = session.speaker_attribution_status
        return {
            "session_id": session_id,
            "mode": session.mode,
            "status": session.status,
            "speaker_attribution_status": attr_status,
            "speaker_attribution": {
                "status": attr_status,
                "speakers_detected": None,
                "speaker_turns": None,
                "segments_updated": None,
                "total_segments": None,
                "coverage": None,
            },
            "speaker_roles": None,
            "objection_handling": [],
            "elapsed_seconds": round(session.elapsed_seconds, 1),
            "health_score": conv.health_score,
            "sentiment": conv.sentiment,
            "sentiment_score": conv.sentiment_score,
            "speaking_ratio": conv.speaking_ratio,
            "participation": conv.participation,
            "filler_count": conv.filler_count,
            "objections": conv.objections,
            "buying_signals": conv.buying_signals,
            "talk_ratio_summary": None,
            "talk_timeline": None,
            "active_alerts": conv.active_alerts,
            "transcript_segments": conv.transcript_segments[-50:],  # last 50 segments
        }

    # DB Fallback
    with profile_stage(session_id, "Dashboard data preparation"):
        db_session = await crud.get_session(db, session_id)
        if db_session is None:
            return JSONResponse(status_code=404, content={"error": "Session not found"})

        # Fetch related telemetry
        segments = await crud.get_transcript_segments(db, session_id, limit=50)
        metrics_list = await crud.get_latest_session_metrics(db, session_id)
        alerts = await crud.get_alerts(db, session_id, limit=50)

        # Reconstruct metrics dictionary
        from typing import Any

        metrics: dict[str, Any] = {
            "health_score": 50,
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "speaking_ratio": {},
            "participation": {},
            "filler_count": 0,
            "objections": [],
            "buying_signals": [],
            # Populated by _persist_attribution_diagnostics after post-session
            # diarization
            "speaker_attribution": None,
            "speaker_roles": None,
            "objection_handling": [],
            "talk_ratio_summary": None,
            "talk_timeline": None,
        }

        for m in metrics_list:
            name = m.metric_name
            val = m.metric_value
            if name in metrics:
                metrics[name] = val

        # For completed/terminal sessions, recalculate speaking metrics from the full
        # set of DB segments
        # to ensure they reflect the post-session Pyannote speaker labels.
        if db_session.status in ["completed", "failed", "interrupted", "expired"]:
            db_segments = await crud.get_all_transcript_segments(db, session_id)
            if db_segments:
                participation = {}
                for seg in db_segments:
                    speaker = seg.speaker_id or "Speaker 1"
                    text = seg.text or ""
                    word_count = len(text.split())
                    participation[speaker] = participation.get(speaker, 0) + word_count

                total_words = sum(participation.values()) or 1
                speaking_ratio = {
                    sp: round((wc / total_words) * 100, 1)
                    for sp, wc in participation.items()
                }
                metrics["participation"] = participation
                metrics["speaking_ratio"] = speaking_ratio

        # Determine elapsed seconds
        elapsed = 0.0
        if db_session.duration is not None:
            elapsed = round(db_session.duration, 1)
        elif db_session.ended_at and db_session.started_at:
            diff = (db_session.ended_at - db_session.started_at).total_seconds()
            elapsed = round(max(0.0, diff), 1)
        else:
            diff = (
                datetime.now(tz=db_session.started_at.tzinfo) - db_session.started_at
            ).total_seconds()
            elapsed = round(max(0.0, diff), 1)

        # Map transcript segments: speaker_id -> speaker, start_time -> start, end_time
        # -> end
        mapped_segments = []
        for s in segments:
            mapped_segments.append(
                {
                    "speaker": s.speaker_id or "Unknown",
                    "text": s.text,
                    "start": round(s.start_time, 2),
                    "end": round(s.end_time, 2),
                    "sentiment": s.sentiment,
                    "sentiment_label": s.sentiment_label,
                }
            )

        # Map alerts: severity -> level, timestamp to Unix epoch
        mapped_alerts = []
        for a in alerts:
            mapped_alerts.append(
                {
                    "level": a.severity,
                    "message": a.message,
                    "timestamp": a.timestamp.timestamp(),
                }
            )

        # Build speaker_attribution nested payload from session_metrics JSONB row
        raw_attribution = metrics.get("speaker_attribution") or {}
        speaker_attribution_payload = {
            "status": db_session.speaker_attribution_status,
            "speakers_detected": raw_attribution.get("speakers_detected"),
            "speaker_turns": raw_attribution.get("speaker_turns"),
            "segments_updated": raw_attribution.get("segments_updated"),
            "total_segments": raw_attribution.get("total_segments"),
            "coverage": raw_attribution.get("coverage_percent"),
        }

        # Load global benchmark health
        import json
        import os

        try:
            from evaluation.thresholds import evaluate_thresholds

            metrics_path = os.path.join(
                os.path.dirname(__file__),
                "evaluation",
                "reports",
                "latest_metrics.json",
            )
            if os.path.exists(metrics_path):
                with open(metrics_path, "r", encoding="utf-8") as f:
                    benchmark_metrics = json.load(f)
                analytics_health = evaluate_thresholds(benchmark_metrics)
            else:
                analytics_health = {
                    "speaker_attribution": "FAIL",
                    "role_classification": "FAIL",
                    "buying_signals": "FAIL",
                    "objections": "FAIL",
                    "objection_handling": "FAIL",
                }
        except Exception:
            analytics_health = {
                "speaker_attribution": "FAIL",
                "role_classification": "FAIL",
                "buying_signals": "FAIL",
                "objections": "FAIL",
                "objection_handling": "FAIL",
            }

        return {
            "session_id": session_id,
            "mode": db_session.mode,
            "status": db_session.status,
            "speaker_attribution_status": db_session.speaker_attribution_status,
            "speaker_attribution": speaker_attribution_payload,
            "speaker_roles": metrics["speaker_roles"],
            "elapsed_seconds": elapsed,
            "health_score": metrics["health_score"],
            "sentiment": metrics["sentiment"],
            "sentiment_score": metrics["sentiment_score"],
            "speaking_ratio": metrics["speaking_ratio"],
            "participation": metrics["participation"],
            "filler_count": metrics["filler_count"],
            "objections": metrics["objections"],
            "buying_signals": metrics["buying_signals"],
            "talk_ratio_summary": metrics["talk_ratio_summary"],
            "talk_timeline": metrics["talk_timeline"],
            "analytics_health": analytics_health,
            "active_alerts": mapped_alerts,
            "transcript_segments": mapped_segments,
        }


# ── Client REST endpoints ─────────────────────────────────────────────────────


class ClientCreateRequest(BaseModel):
    """Request body for POST /clients — mirrors the API Contract schema."""

    name: str
    industry: str | None = None


@app.post("/clients", status_code=201, tags=["Clients"])
async def post_client(
    body: ClientCreateRequest,
    db: _AsyncSession = _Depends(_get_db),
):
    """
    Create a new client profile.

    Request:  { name, industry? }
    Response 201: { id, name, industry, created_at }
    Auth: deferred to Phase 5 — user_id is NULL for now.
    """
    from db.crud import create_client as _crud_create_client

    row = await _crud_create_client(
        db,
        name=body.name,
        industry=body.industry,
    )
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "name": row.name,
        "industry": row.industry,
        "created_at": row.created_at.isoformat(),
    }


@app.get("/clients", tags=["Clients"])
async def get_clients(
    db: _AsyncSession = _Depends(_get_db),
):
    """
    List all client profiles.

    Response 200: [ { id, name, industry, created_at }, ... ]
    Auth: deferred to Phase 5 — returns all clients (no user scope yet).
    """
    from db.crud import list_clients as _crud_list_clients

    rows = await _crud_list_clients(db)
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "industry": row.industry,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.get("/clients/{client_id}", tags=["Clients"])
async def get_client(
    client_id: str,
    db: _AsyncSession = _Depends(_get_db),
):
    """
    Get client briefing card.

    Response 200: {
        client_id, name, meetings_count,
        sentiment_trend, common_objections, last_meeting_date
    }
    Briefing data is sourced from the latest client_snapshots row.
    If no snapshot exists yet (no completed sessions), safe defaults are returned.
    """
    from sqlalchemy import select

    from db.crud import get_client as _crud_get_client
    from db.models import ClientSnapshot

    row = await _crud_get_client(db, client_id)
    if row is None:
        return JSONResponse(status_code=404, content={"error": "Client not found"})

    # Load the latest snapshot for this client (may not exist yet)
    snap_result = await db.execute(
        select(ClientSnapshot)
        .where(ClientSnapshot.client_id == row.id)
        .order_by(ClientSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()

    return {
        "client_id": str(row.id),
        "name": row.name,
        "industry": row.industry,
        "meetings_count": snap.meetings_count if snap else 0,
        "sentiment_trend": snap.sentiment_trend if snap else None,
        "common_objections": snap.common_objections if snap else [],
        "last_meeting_date": (
            snap.last_meeting_date.isoformat()
            if snap and snap.last_meeting_date
            else None
        ),
        "summary": snap.summary if snap else None,
    }


# ── Legacy batch analysis endpoint (kept for compatibility) ───────────────────
@app.post("/analyze", tags=["Legacy"])
async def analyze_audio(
    file: UploadFile = File(...),
    mode: str = Form("meeting"),
    client_id: str | None = Form(None),
    db: _AsyncSession = _Depends(_get_db),
):
    """
    Legacy batch audio analysis endpoint.
    Kept for backward compatibility with the original batch upload flow.
    For real-time analysis, use the WebSocket pipeline.
    """
    import shutil
    import uuid
    from datetime import datetime, timezone

    from db import crud
    from services.context_analyzer import analyze_meeting, analyze_sales
    from services.nlp_engine import get_nlp_engine

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in the uploaded file.",
        )

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
        if not isinstance(raw_segments, list):
            raw_segments = []

        nlp = get_nlp_engine()
        enriched_segments = await run_in_threadpool(nlp.enrich_transcript, raw_segments)

        final_transcript = {
            "text": raw_transcript_data.get("text", ""),
            "segments": enriched_segments,
        }

        if mode == "sales":
            insights = await run_in_threadpool(analyze_sales, enriched_segments)
        else:
            insights = await run_in_threadpool(analyze_meeting, final_transcript)

        # ── Persist the session to PostgreSQL immediately ──
        session_id = str(uuid.uuid4())
        db_session = await crud.create_session(
            db,
            session_id=session_id,
            mode=mode,
            client_id=client_id,
            title=file.filename or "Uploaded Session",
        )
        db_session.status = "completed"
        db_session.duration = enriched_segments[-1]["end"] if enriched_segments else 0.0
        db_session.ended_at = datetime.now(timezone.utc)

        # Save transcript segments
        for seg in enriched_segments:
            from db.models import TranscriptSegment as DBTranscriptSegment

            db_seg = DBTranscriptSegment(
                session_id=uuid.UUID(session_id),
                speaker_id="Speaker A",
                start_time=seg.get("start", 0.0),
                end_time=seg.get("end", 0.0),
                text=seg.get("text", ""),
                sentiment=seg.get("sentiment", 0.0),
                sentiment_label=seg.get("sentiment_label", "Neutral"),
            )
            db.add(db_seg)

        # Save metrics
        q_score = (
            insights.get("quality", {}).get("score", 5)
            if isinstance(insights.get("quality"), dict)
            else 5
        )
        metrics_to_save = [
            {"metric_name": "health_score", "metric_value": int(q_score * 10)},
            {
                "metric_name": "sentiment_score",
                "metric_value": insights.get("sentiment_score", 0.0),
            },
            {
                "metric_name": "objections",
                "metric_value": insights.get("objections", []),
            },
            {
                "metric_name": "buying_signals",
                "metric_value": (
                    insights.get("buying_signals", [])
                    if "buying_signals" in insights
                    else []
                ),
            },
            {"metric_name": "speaking_ratio", "metric_value": {"Speaker A": 100.0}},
            {"metric_name": "participation", "metric_value": {"Speaker A": 100.0}},
        ]
        await crud.save_session_metrics_batch(db, session_id, metrics_to_save)

        # Save analysis result summary
        from db.models import AnalysisResult as DBAnalysisResult

        analysis_res = DBAnalysisResult(
            session_id=uuid.UUID(session_id),
            health_score=int(q_score * 10),
            summary=insights.get("summary", ""),
            report_json=insights,
        )
        db.add(analysis_res)

        await db.commit()

        # Update client memory if client_id is linked
        if client_id:
            from services.client_memory import update_client_memory

            await update_client_memory(db, uuid.UUID(client_id))
            await db.commit()

        return JSONResponse(
            content={
                "filename": file.filename,
                "mode": mode,
                "transcript": final_transcript,
                "insights": insights,
            }
        )

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# reload touch
