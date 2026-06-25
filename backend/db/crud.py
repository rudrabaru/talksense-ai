"""
TalkSense AI v4 — Database CRUD Layer (Phase 3)

All functions are async and accept an AsyncSession injected via Depends(get_db)
or opened directly with AsyncSessionLocal() inside background tasks.

Implementation is staged across phases:

    Phase 1 (complete):
        create_session()        — persist a new session row on POST /sessions
        get_session()           — look up a session row by UUID
        update_session_status() — transition status + set ended_at / duration

    Phase 2 (complete):
        create_client()         — create a client profile row
        get_client()            — fetch a client row by UUID string
        list_clients()          — list all clients, optionally filtered by user

    Phase 3 (complete):
        save_transcript_segments()   — batch-stage new transcript segment rows
        save_session_metrics_batch() — batch-stage multiple metric snapshot rows
        save_alerts_batch()          — batch-stage multiple alert event rows
        save_analysis_result()       — atomic PostgreSQL upsert for final analysis
        update_client_snapshot()     — append a new client briefing snapshot row
        recover_stale_sessions()     — bulk-transition orphaned active sessions on startup

Design rules (from .agent/ARCHITECTURE.md + database_agent.md):
    - All functions are async; no sync SQLAlchemy calls
    - Input types match the in-memory SessionState in ws/session_manager.py
    - No business logic — pure DB reads/writes; logic stays in session_manager

Transaction ownership rules (Approved CRUD Refactor Design):
    - HTTP route handlers own the transaction boundary for request-scoped writes:
          await crud.create_session(db, ...)
          await db.commit()
          await db.refresh(row)
    - The background flusher owns the transaction boundary for telemetry writes:
          await crud.save_transcript_segments(db, ...)
          await crud.save_session_metrics_batch(db, ...)
          await crud.save_alerts_batch(db, ...)
          await db.commit()         # single commit covers all three
          session.last_flushed_segment_index += len(delta)  # advance watermarks AFTER commit
    - recover_stale_sessions() is a self-contained startup task and manages its
      own commit internally since it runs in isolation before any flusher starts.
    - Callers are responsible for advancing watermarks AFTER commit succeeds
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import select, update, CursorResult
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Session as _DBSession

from db.models import Alert as DBAlert
from db.models import AnalysisResult as DBAnalysisResult
from db.models import Client as DBClient
from db.models import ClientSnapshot as DBClientSnapshot
from db.models import Session as DBSession
from db.models import SessionMetric as DBSessionMetric
from db.models import TranscriptSegment as DBTranscriptSegment

logger = logging.getLogger(__name__)

# ── Terminal status set ───────────────────────────────────────────────────────
# Used to decide whether ended_at / duration should be stamped on update.
_TERMINAL_STATUSES = frozenset(
    {"completed", "failed", "interrupted", "expired"}
)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Session lifecycle
# ─────────────────────────────────────────────────────────────────────────────


async def create_session(
    db: AsyncSession,
    *,
    session_id: str,          # UUID string from ws/session_manager.py
    mode: str,                # "meeting" | "sales" | "interview"
    client_id: str | None = None,
    user_id: int | None = None,
    title: str | None = None,
) -> DBSession:
    """
    Stage a new session row for insertion.

    Called immediately after SessionManager.create() inside POST /sessions.
    Does NOT commit — the route handler calls db.commit() and db.refresh()
    after this function returns, so the HTTP response reflects DB-generated
    timestamps and the server-default UUID.

    Args:
        db:         Open AsyncSession (injected via Depends(get_db)).
        session_id: UUID string that matches the in-memory SessionState.
                    Stored as PostgreSQL uuid — converted here to uuid.UUID.
        mode:       Conversation mode — "meeting", "sales", or "interview".
        client_id:  Optional client UUID string; NULL if no client is linked.
        user_id:    Optional user integer PK; NULL until auth is active.
        title:      Optional human-readable session label.

    Returns:
        Staged DBSession ORM object (not yet committed).
        Caller must call await db.commit() then await db.refresh(row).
    """
    row = DBSession(
        id=uuid.UUID(session_id),
        mode=mode,
        client_id=uuid.UUID(client_id) if client_id else None,
        user_id=user_id,
        title=title,
        status="created",
    )
    db.add(row)
    logger.info("DB — session %s staged [mode=%s]", session_id[:8], mode)
    return row


async def get_session(
    db: AsyncSession,
    session_id: str,
) -> DBSession | None:
    """
    Fetch a session row by its UUID string.

    Returns the DBSession ORM object if found, or None.  The caller is
    responsible for raising 404 errors — this function stays pure data access.

    Args:
        db:         Open AsyncSession.
        session_id: UUID string to look up.

    Returns:
        DBSession | None
    """
    result = await db.execute(
        select(DBSession).where(DBSession.id == uuid.UUID(session_id))
    )
    row = result.scalar_one_or_none()
    if row is None:
        logger.debug("DB — session %s not found", session_id[:8])
    return row


async def update_session_status(
    db: AsyncSession,
    session_id: str,
    status: str,
    *,
    duration: float | None = None,
) -> DBSession | None:
    """
    Stage a status transition on a persisted session row.

    When status is terminal (completed / failed / interrupted / expired):
        - Sets ended_at to the current UTC timestamp.
        - Sets duration to the elapsed seconds provided by the caller
          (sourced from SessionState.elapsed_seconds in session_manager.py).

    Does NOT commit — the route handler or termination coordinator calls
    db.commit() after this function returns.

    Args:
        db:         Open AsyncSession.
        session_id: UUID string of the session to update.
        status:     New status string (must match SessionStatus enum values).
        duration:   Elapsed session duration in seconds — required when
                    status is a terminal value, ignored otherwise.

    Returns:
        Updated DBSession row (not yet committed), or None if not found in DB.
    """
    row = await get_session(db, session_id)
    if row is None:
        logger.warning(
            "DB — update_session_status: session %s not found", session_id[:8]
        )
        return None

    row.status = status

    if status in _TERMINAL_STATUSES:
        row.ended_at = datetime.now(tz=timezone.utc)
        if duration is not None:
            row.duration = round(duration, 3)

    logger.info(
        "DB — session %s status staged → %s", session_id[:8], status
    )
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Client management
# ─────────────────────────────────────────────────────────────────────────────


async def create_client(
    db: AsyncSession,
    *,
    name: str,
    industry: str | None = None,
    user_id: int | None = None,
) -> DBClient:
    """
    Stage a new client profile for insertion.

    Called from POST /clients.  Does NOT commit — the route handler calls
    db.commit() and db.refresh() to populate the server-generated UUID and
    created_at before returning the HTTP response.

    Args:
        db:         Open AsyncSession.
        name:       Client display name (company or individual).
        industry:   Optional industry label (e.g. "Software", "Finance").
        user_id:    Optional FK to users.id — NULL until auth is active.

    Returns:
        Staged DBClient ORM object (not yet committed).
        Caller must call await db.commit() then await db.refresh(row).
    """
    row = DBClient(
        name=name,
        industry=industry,
        user_id=user_id,
    )
    db.add(row)
    logger.info("DB — client staged [name=%r]", name)
    return row


async def get_client(
    db: AsyncSession,
    client_id: str,
) -> DBClient | None:
    """
    Fetch a client row by its UUID string.

    Returns DBClient if found, or None.  The caller is responsible for
    converting None into a 404 HTTP response.

    Args:
        db:         Open AsyncSession.
        client_id:  UUID string of the client to retrieve.

    Returns:
        DBClient | None
    """
    result = await db.execute(
        select(DBClient).where(DBClient.id == uuid.UUID(client_id))
    )
    row = result.scalar_one_or_none()
    if row is None:
        logger.debug("DB — client %s not found", client_id[:8])
    return row


async def list_clients(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DBClient]:
    """
    Return a paginated list of client rows.

    When user_id is provided the result is filtered to clients owned by that
    user.  When user_id is None (Phase 3, no auth yet) all client rows are
    returned — this behaviour will be scoped per-user when JWT auth is active.

    Args:
        db:       Open AsyncSession.
        user_id:  Optional filter — only return clients for this user.
        limit:    Maximum number of rows to return (default 100).
        offset:   Pagination offset (default 0).

    Returns:
        List of DBClient ORM objects (may be empty).
    """
    query = select(DBClient).order_by(DBClient.created_at.desc())

    if user_id is not None:
        query = query.where(DBClient.user_id == user_id)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    rows = list(result.scalars().all())
    logger.debug("DB — list_clients returned %d rows", len(rows))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Flusher persistence functions
# ─────────────────────────────────────────────────────────────────────────────
#
# Transaction ownership for all functions below belongs to the CALLER (the
# background flusher).  The flusher pattern is:
#
#   async with AsyncSessionLocal() as db:
#       await save_transcript_segments(db, session_id, seg_delta)
#       await save_session_metrics_batch(db, session_id, metric_dicts)
#       await save_alerts_batch(db, session_id, alert_delta)
#       await db.commit()
#       # advance watermarks only AFTER commit succeeds
#
# None of the functions below call db.commit() or db.refresh().
# ─────────────────────────────────────────────────────────────────────────────


async def save_transcript_segments(
    db: AsyncSession,
    session_id: str,
    segments: list[dict],
) -> None:
    """
    Batch-stage a list of transcript segment dicts as TranscriptSegment rows.

    Called by the background flusher with the delta slice
    conversation.transcript_segments[last_flushed_segment_index:].  The caller
    must advance last_flushed_segment_index ONLY after db.commit() returns
    without raising (deferred watermark pattern).

    Does NOT commit and does NOT refresh.  The flusher owns the commit
    boundary so that segments, metrics, and alerts are written atomically in
    one transaction per flush cycle.

    Each dict is expected to carry the keys emitted by the audio pipeline:
        speaker_id      str | None
        start_time      float
        end_time        float
        text            str
        sentiment       float | None
        sentiment_label str | None

    Args:
        db:         Open AsyncSession (created by the flusher via AsyncSessionLocal).
        session_id: UUID string of the owning session.
        segments:   List of segment dicts to insert.  Empty list is a no-op.
    """
    if not segments:
        return

    sid = uuid.UUID(session_id)
    rows = [
        DBTranscriptSegment(
            session_id=sid,
            speaker_id=seg.get("speaker", seg.get("speaker_id")),
            start_time=seg.get("start", seg.get("start_time", 0.0)),
            end_time=seg.get("end", seg.get("end_time", 0.0)),
            text=seg.get("text", ""),
            sentiment=seg.get("sentiment"),
            sentiment_label=seg.get("sentiment_label"),
        )
        for seg in segments
    ]
    db.add_all(rows)
    logger.debug(
        "DB — %d transcript segment(s) staged for session %s",
        len(rows), session_id[:8],
    )


async def save_session_metrics_batch(
    db: AsyncSession,
    session_id: str,
    metrics: list[dict],
) -> None:
    """
    Batch-stage multiple point-in-time metric snapshot rows.

    Replaces the deprecated single-row save_metric().  Called by the flusher
    when the MD5 hash of the current metrics dict differs from
    last_flushed_metric_hash.  Each entry in `metrics` represents one
    metric_name / metric_value pair captured at the current flush time.

    Does NOT commit and does NOT refresh.  The flusher owns the commit
    boundary so that all telemetry types are written atomically per cycle.

    Each dict is expected to carry:
        metric_name   str   — e.g. "health_score", "participation"
        metric_value  Any   — scalar or structured value stored as JSONB

    The row timestamp defaults to the database server clock (server_default
    func.now()) so each row reflects actual flush time — not Python time.

    Args:
        db:           Open AsyncSession.
        session_id:   UUID string of the owning session.
        metrics:      List of metric dicts.  Empty list is a no-op.
    """
    if not metrics:
        return

    sid = uuid.UUID(session_id)
    rows = [
        DBSessionMetric(
            session_id=sid,
            metric_name=m["metric_name"],
            metric_value=m["metric_value"],
        )
        for m in metrics
    ]
    db.add_all(rows)
    logger.debug(
        "DB — %d metric row(s) staged for session %s",
        len(rows), session_id[:8],
    )


async def save_alerts_batch(
    db: AsyncSession,
    session_id: str,
    alerts: list[dict],
) -> None:
    """
    Batch-stage multiple alert event rows.

    Replaces the deprecated single-row save_alert().  Called by the flusher
    with the delta slice conversation.active_alerts[last_flushed_alert_index:].
    The caller must advance last_flushed_alert_index ONLY after db.commit()
    returns without raising.

    Does NOT commit and does NOT refresh.  The flusher owns the commit
    boundary so that segments, metrics, and alerts are written atomically in
    one transaction per flush cycle.

    Each dict is expected to carry:
        type        str | None   — e.g. "long_silence", "sentiment_crash"
        severity    str          — "critical" | "warning" | "info"
        message     str
        timestamp   str | datetime | None — ISO-8601 string, datetime, or None

    Args:
        db:         Open AsyncSession.
        session_id: UUID string of the owning session.
        alerts:     List of alert dicts.  Empty list is a no-op.
    """
    if not alerts:
        return

    sid = uuid.UUID(session_id)
    rows = []
    for alert in alerts:
        # Normalise timestamp: accept epoch float, ISO string, datetime object, or None
        ts = alert.get("timestamp")
        if isinstance(ts, (float, int)):
            ts = datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(tz=timezone.utc)
            
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        rows.append(DBAlert(
            session_id=sid,
            type=alert.get("alert_type", alert.get("type")),
            severity=alert.get("level", alert.get("severity", "info")),
            message=alert.get("message", ""),
            timestamp=ts,
        ))

    db.add_all(rows)
    logger.debug(
        "DB — %d alert(s) staged for session %s",
        len(rows), session_id[:8],
    )


async def save_analysis_result(
    db: AsyncSession,
    session_id: str,
    *,
    health_score: int | None = None,
    summary: str | None = None,
    report_json: dict | None = None,
) -> None:
    """
    Atomically upsert the one-to-one final analysis report for a session.

    Uses a PostgreSQL-native INSERT ... ON CONFLICT DO UPDATE statement so
    that the entire check-and-write is performed by the database engine in a
    single round-trip.  This eliminates the SELECT + conditional INSERT/UPDATE
    TOCTOU race condition present in the previous implementation.

    Written exactly once when the session transitions to COMPLETED.  On a
    retry (e.g. after a transient commit failure), the ON CONFLICT clause
    updates the existing row rather than violating the UNIQUE constraint on
    analysis_results.session_id.

    Does NOT commit and does NOT refresh.  The termination handler owns the
    commit boundary and is responsible for advancing state after success.

    Conflict target: analysis_results.session_id (UNIQUE constraint).
    On conflict: overwrites health_score, summary, report_json.

    Args:
        db:           Open AsyncSession.
        session_id:   UUID string of the owning session.
        health_score: Final health score integer (0–100).
        summary:      Plain-text executive summary.
        report_json:  Full structured report dict (decisions, action_items, etc.).
    """
    sid = uuid.UUID(session_id)

    stmt = (
        pg_insert(DBAnalysisResult)
        .values(
            session_id=sid,
            health_score=health_score,
            summary=summary,
            report_json=report_json,
        )
        .on_conflict_do_update(
            index_elements=["session_id"],
            set_={
                "health_score": health_score,
                "summary": summary,
                "report_json": report_json,
            },
        )
    )
    await db.execute(stmt)
    logger.info(
        "DB — analysis_result upsert staged for session %s [health=%s]",
        session_id[:8], health_score,
    )


async def update_client_snapshot(
    db: AsyncSession,
    client_id: str,
    *,
    summary: str | None = None,
    sentiment_score: float | None = None,
    sentiment_trend: str | None = None,
    meetings_count: int = 0,
    last_meeting_date: datetime | None = None,
    common_objections: list | None = None,
) -> None:
    """
    Stage a new client briefing snapshot row for insertion.

    A new row is always inserted (append-only pattern) rather than updating
    the existing row.  The GET /clients/{client_id} route selects the latest
    row via ORDER BY snapshot_date DESC LIMIT 1, so historical rows are
    preserved for audit without any DELETE logic.

    Does NOT commit and does NOT refresh.  The termination handler owns the
    commit boundary and is responsible for advancing state after success.

    Args:
        db:                Open AsyncSession.
        client_id:         UUID string of the client to snapshot.
        summary:           Plain-text client briefing summary.
        sentiment_score:   Floating-point aggregated sentiment (–1.0 to 1.0).
        sentiment_trend:   "improving" | "stable" | "declining".
        meetings_count:    Total completed meetings for this client.
        last_meeting_date: UTC datetime of the most recent completed session.
        common_objections: JSONB list of objection strings.
    """
    row = DBClientSnapshot(
        client_id=uuid.UUID(client_id),
        summary=summary,
        sentiment_score=sentiment_score,
        sentiment_trend=sentiment_trend,
        meetings_count=meetings_count,
        last_meeting_date=last_meeting_date,
        common_objections=common_objections,
    )
    db.add(row)
    logger.info(
        "DB — client_snapshot staged for client %s [meetings=%d]",
        client_id[:8], meetings_count,
    )


async def recover_stale_sessions(db: AsyncSession) -> int:
    """
    Startup recovery: bulk-transition orphaned active sessions to INTERRUPTED.
    Also finalizes and links any partial WAV audio files on disk.

    Runs once during the FastAPI lifespan startup hook (before flusher loop
    starts) to clean up sessions left in non-terminal states from a prior
    server crash or unexpected shutdown.

    This is the ONLY flusher-facing function that manages its own commit.
    It runs as an isolated, synchronous startup step before any flusher or
    route handler is active, so there is no caller context to delegate to.

    Transitions:
        created     → interrupted
        connecting  → interrupted
        active      → interrupted
        processing  → interrupted

    Args:
        db: Open AsyncSession.

    Returns:
        Number of session rows updated.
    """
    import os
    import struct

    _STALE_STATUSES = ("created", "connecting", "active", "processing")

    # Fetch stale sessions to finalize their WAV files if they exist
    result = await db.execute(
        select(DBSession).where(DBSession.status.in_(_STALE_STATUSES))
    )
    stale_sessions = result.scalars().all()

    affected = 0
    for session in stale_sessions:
        session.status = "interrupted"
        session.ended_at = datetime.now(tz=timezone.utc)

        # Formulate deterministic WAV file path
        session_id_str = str(session.id)
        safe_id = session_id_str.replace("-", "")[:16]
        wav_filename = f"session_{safe_id}.wav"
        wav_path = os.path.join("session_audio", wav_filename)

        if os.path.exists(wav_path):
            try:
                # Finalize WAV header sizes based on file size on disk
                file_size = os.path.getsize(wav_path)
                if file_size >= 44:
                    data_bytes = file_size - 44
                    with open(wav_path, "r+b") as f:
                        f.seek(4)
                        f.write(struct.pack("<I", 36 + data_bytes))
                        f.seek(40)
                        f.write(struct.pack("<I", data_bytes))
                    logger.info(
                        "DB — finalized WAV header for recovered session %s [size=%d]",
                        session_id_str[:8], file_size
                    )
                session.audio_file_path = os.path.abspath(wav_path)
            except Exception as exc:
                logger.error(
                    "DB — failed to finalize WAV for recovered session %s: %s",
                    session_id_str[:8], exc
                )

        affected += 1

    if affected > 0:
        await db.commit()
        logger.warning(
            "DB — startup recovery: %d stale session(s) marked as interrupted",
            affected,
        )
    else:
        logger.info("DB — startup recovery: no stale sessions found.")

    return affected


async def get_transcript_segments(
    db: AsyncSession,
    session_id: str,
    limit: int = 50,
) -> list[DBTranscriptSegment]:
    """
    Fetch the last `limit` transcript segments for a session.
    Returns them ordered chronologically by start_time (ascending).
    """
    sid = uuid.UUID(session_id)
    stmt = (
        select(DBTranscriptSegment)
        .where(DBTranscriptSegment.session_id == sid)
        .order_by(DBTranscriptSegment.start_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


async def get_latest_session_metrics(
    db: AsyncSession,
    session_id: str,
) -> list[DBSessionMetric]:
    """
    Fetch the latest value for each metric name for the session.
    """
    sid = uuid.UUID(session_id)
    stmt = (
        select(DBSessionMetric)
        .distinct(DBSessionMetric.metric_name)
        .where(DBSessionMetric.session_id == sid)
        .order_by(DBSessionMetric.metric_name, DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_alerts(
    db: AsyncSession,
    session_id: str,
    limit: int = 50,
) -> list[DBAlert]:
    """
    Fetch the last `limit` alerts for a session, ordered by timestamp descending.
    """
    sid = uuid.UUID(session_id)
    stmt = (
        select(DBAlert)
        .where(DBAlert.session_id == sid)
        .order_by(DBAlert.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Post-session speaker attribution helpers
# ─────────────────────────────────────────────────────────────────────────────


async def update_session_audio_path(
    db: AsyncSession,
    session_id: str,
    audio_file_path: str,
) -> None:
    """
    Persist the WAV file path written during the live session.

    Called once at session end after AudioBuffer.flush_remaining() has
    finalised the file.  Does NOT commit — the caller owns the transaction.

    Args:
        db:              Open AsyncSession.
        session_id:      UUID string of the owning session.
        audio_file_path: Absolute path to the finalised WAV file.
    """
    stmt = (
        update(_DBSession)
        .where(_DBSession.id == uuid.UUID(session_id))
        .values(audio_file_path=audio_file_path)
        .execution_options(synchronize_session=False)
    )
    await db.execute(stmt)
    logger.debug(
        "DB — audio_file_path staged for session %s [path=%s]",
        session_id[:8], audio_file_path,
    )


async def update_session_speaker_attribution_status(
    db: AsyncSession,
    session_id: str,
    status: str,
) -> None:
    """
    Update the speaker_attribution_status field on the session row.

    Valid status values: "pending" | "processing" | "completed" | "failed"

    Does NOT commit — the caller owns the transaction.  The post-session
    diarizer opens its own AsyncSessionLocal() and commits after each
    status transition so that failures are observable.

    Args:
        db:         Open AsyncSession.
        session_id: UUID string of the owning session.
        status:     New attribution lifecycle status string.
    """
    stmt = (
        update(_DBSession)
        .where(_DBSession.id == uuid.UUID(session_id))
        .values(speaker_attribution_status=status)
        .execution_options(synchronize_session=False)
    )
    await db.execute(stmt)
    logger.debug(
        "DB — speaker_attribution_status staged → %s for session %s",
        status, session_id[:8],
    )


async def get_all_transcript_segments(
    db: AsyncSession,
    session_id: str,
) -> list[DBTranscriptSegment]:
    """
    Fetch ALL transcript segments for a session ordered by start_time.

    Used by the post-session diarizer which needs the complete segment
    list to assign speaker labels globally.  Unlike get_transcript_segments()
    there is no LIMIT applied.

    Args:
        db:         Open AsyncSession.
        session_id: UUID string of the owning session.

    Returns:
        List of DBTranscriptSegment rows ordered by start_time ascending.
    """
    sid = uuid.UUID(session_id)
    stmt = (
        select(DBTranscriptSegment)
        .where(DBTranscriptSegment.session_id == sid)
        .order_by(DBTranscriptSegment.start_time)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_segment_speakers(
    db: AsyncSession,
    session_id: str,
    speaker_updates: list[dict],
) -> int:
    """
    Batch-update the speaker_id field of existing transcript_segment rows.

    Only modifies speaker_id — text, start_time, end_time, and sentiment
    fields are never touched.

    All updates are staged within the same db session so that the caller
    can commit them atomically in a single round-trip.

    Does NOT commit — the caller owns the transaction.

    Args:
        db:              Open AsyncSession.
        session_id:      UUID string of the owning session (used for logging).
        speaker_updates: List of dicts, each with keys:
                           segment_id (int)  — primary key of the row
                           speaker     (str) — new speaker label

    Returns:
        Number of rows updated.
    """
    if not speaker_updates:
        return 0

    count = 0
    for item in speaker_updates:
        seg_id  = item["segment_id"]
        speaker = item["speaker"]
        stmt = (
            update(DBTranscriptSegment)
            .where(DBTranscriptSegment.id == seg_id)
            .values(speaker_id=speaker)
            .execution_options(synchronize_session=False)
        )
        await db.execute(stmt)
        count += 1

    logger.debug(
        "DB — %d segment speaker_id update(s) staged for session %s",
        count, session_id[:8],
    )
    return count


async def list_sessions_paginated(
    db: AsyncSession,
    *,
    mode: str | None = None,
    status: str | None = None,
    client_id: str | None = None,
    search: str | None = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10,
) -> tuple[list[dict], int]:
    """
    List historical sessions with search, filtering, sorting, and pagination.
    Returns a tuple of (items_list, total_count).
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    # 1. Base query for sessions and count
    stmt = select(DBSession).outerjoin(DBSession.client).options(joinedload(DBSession.client))
    count_stmt = select(func.count(DBSession.id)).outerjoin(DBSession.client)

    # 2. Filters
    filters = []
    if status:
        filters.append(DBSession.status == status)
    if mode:
        filters.append(DBSession.mode == mode)
    if client_id:
        try:
            filters.append(DBSession.client_id == uuid.UUID(client_id))
        except ValueError:
            return [], 0

    if search:
        search_filter = (
            DBSession.title.ilike(f"%{search}%") |
            DBSession.mode.ilike(f"%{search}%") |
            DBClient.name.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    # 3. Get total count
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # 4. Sort
    allowed_sort_fields = {
        "started_at": DBSession.started_at,
        "duration": DBSession.duration,
        "title": DBSession.title,
        "status": DBSession.status,
        "mode": DBSession.mode,
    }
    sort_col = allowed_sort_fields.get(sort_by, DBSession.started_at)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    # 5. Paginate
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    # 6. Execute query
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    if not sessions:
        return [], total

    # 7. Batch fetch latest metrics (health_score and sentiment)
    session_ids = [s.id for s in sessions]

    subq = (
        select(
            DBSessionMetric.session_id,
            DBSessionMetric.metric_name,
            DBSessionMetric.metric_value,
            func.row_number().over(
                partition_by=(DBSessionMetric.session_id, DBSessionMetric.metric_name),
                order_by=(DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc())
            ).label("rn")
        )
        .where(
            DBSessionMetric.session_id.in_(session_ids),
            DBSessionMetric.metric_name.in_(["health_score", "sentiment"])
        )
    ).subquery()

    metrics_stmt = select(subq).where(subq.c.rn == 1)
    metrics_result = await db.execute(metrics_stmt)
    metrics_rows = metrics_result.all()

    metrics_map = {}
    for row in metrics_rows:
        sid_str = str(row.session_id)
        if sid_str not in metrics_map:
            metrics_map[sid_str] = {}
        metrics_map[sid_str][row.metric_name] = row.metric_value

    # 8. Construct response summaries
    items = []
    for s in sessions:
        sid_str = str(s.id)
        session_metrics = metrics_map.get(sid_str, {})

        health_score = session_metrics.get("health_score")
        if not isinstance(health_score, int) and health_score is not None:
            try:
                health_score = int(health_score)
            except (ValueError, TypeError):
                health_score = None

        sentiment = session_metrics.get("sentiment")
        if not isinstance(sentiment, str) and sentiment is not None:
            sentiment = str(sentiment)

        items.append({
            "session_id": sid_str,
            "mode": s.mode,
            "status": s.status,
            "title": s.title,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "duration": s.duration,
            "client_id": str(s.client_id) if s.client_id else None,
            "client_name": s.client.name if s.client else None,
            "health_score": health_score,
            "sentiment": sentiment,
        })

    return items, total


