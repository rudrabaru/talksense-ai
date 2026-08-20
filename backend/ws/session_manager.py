r"""
TalkSense AI — Session Manager

Owns the lifecycle of every active session.
Each session has:
  - A unique session_id (UUID)
  - A status (Created → Connecting → Active → Processing → Completed)
  - An AudioBuffer for accumulating PCM chunks
  - An in-memory ConversationState (metrics, alerts, transcript)
  - A reference to the broadcast WebSocket connections

Thread-safety: asyncio.Lock per session for state mutation.

Background Flusher:
  A global scheduler loop (_flush_loop) fires every FLUSH_INTERVAL_SECONDS.
  For each non-terminal, non-flushing session it launches an isolated
  _flush_session() coroutine guarded by _FLUSH_SEMAPHORE (max 5 concurrent).

  Alert persistence — eviction-safe ID-set + alert_log strategy:
    active_alerts is a bounded eviction window (max 3), NOT append-only.
    Index watermarks are invalid, and reading active_alerts alone will miss
    alerts that were born and evicted between two flush ticks.

    To close this gap, every alert dict seen in active_alerts at flush time
    is merged into SessionState.alert_log — a dict[id, alert_dict] that
    grows monotonically and is never evicted.  The flusher then operates on
    alert_log rather than active_alerts:

      alert_delta = {id: d for id, d in alert_log.items()
                     if id not in flushed_alert_ids}

    Any alert that appears in active_alerts at least once before it is
    evicted will be captured in alert_log and eventually persisted.
    Alerts that are born AND evicted within a single 5-second gap between
    flush ticks cannot be recovered without modifying the alert engine
    (out of scope for this module).

    flushed_alert_ids is union-updated after db.commit() succeeds.

  Per-session flush sequence:
    1. Acquire _FLUSH_SEMAPHORE — throttles concurrent DB connections.
    2. Acquire session.lock — merge active_alerts into alert_log, snapshot
       delta (segs, metrics, alert_log \ flushed_alert_ids).
    3. Release session.lock immediately — DB IO runs outside the lock.
    4. Open a fresh AsyncSessionLocal() context.
    5. Stage all pending writes (segments, metrics, alerts) via CRUD.
    6. db.commit() — single atomic transaction per flush cycle.
    7. Advance watermarks ONLY after commit succeeds:
       - last_flushed_segment_index += len(seg_delta)
       - flushed_alert_ids |= {id for id in alert_delta}
    8. Clear session.is_flushing.

  On any exception:
    - The DB transaction rolls back (context manager handles this).
    - Watermarks are NOT advanced — data will be retried next cycle.
    - Periodic path: error is logged; audio pipeline is never interrupted.
    - Final path: exception is RE-RAISED so end() propagates it to the
      route handler.  No silent data-loss on session termination.

  Session Termination (end() sequence):
    1. Await session._flush_idle — an asyncio.Event that is SET whenever
       no periodic flush is running.  Blocks instantly if idle; otherwise
       suspends until _do_flush's exit path sets it.  Replaces the
       previous spin-poll on is_flushing.  Bounded by END_TIMEOUT_SECONDS.
    2. Set terminal status under session.lock.
    3. If a final flush for this session is already in-flight (duplicate
       end() call or retry), reuse the existing task instead of creating
       a new one — prevents duplicate DB writes.
    4. Launch _flush_session_final() as a tracked task (registered in
       _flush_workers so stop_flusher() sees it), then await it.
       Bounded by END_TIMEOUT_SECONDS.
    5. Re-raise any timeout or DB failure so the route handler can surface
       a 5xx response.  No silent data-loss.

  Shutdown (stop_flusher() sequence):
    1. Cancel the scheduler loop — no new tasks can be spawned after this.
    2. Await loop cancellation.
    3. Primary drain — asyncio.gather over a snapshot of _flush_workers,
       bounded by SHUTDOWN_TIMEOUT_SECONDS.  Covers all workers registered
       before the snapshot.
    4. Secondary drain — yield once (asyncio.sleep(0)) then drain any
       workers that registered during the primary gather.  This closes the
       window where a concurrent end() call creates a final-flush task
       AFTER the snapshot was taken but BEFORE stop_flusher() returns.
       Bounded by CANCEL_DRAIN_TIMEOUT_SECONDS.

  Lifecycle:
    - start_flusher()  → called from main.py lifespan startup.
      Initialises _FLUSH_SEMAPHORE on the running event loop.
    - stop_flusher()   → called from main.py lifespan shutdown.
      MUST complete before engine.dispose() to prevent pool disposal
      racing with active DB connections.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import WebSocket

from audio.buffer import AudioBuffer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Flusher configuration ─────────────────────────────────────────────────────
# Interval between flush cycles in seconds.
FLUSH_INTERVAL_SECONDS: float = 5.0

# Maximum concurrent flush coroutines across all sessions.
# Caps DB connection usage to avoid competing with the Whisper/Pyannote GPU pipeline.
# IMPORTANT: Initialized to None at import time — must be created on the
# running event loop inside start_flusher() to avoid event-loop mismatch
# errors in tests and multi-worker deployments.
_FLUSH_SEMAPHORE: asyncio.Semaphore | None = None
_FLUSH_SEMAPHORE_LIMIT: int = 5

# Maximum seconds end() will wait for an in-flight flush to drain and for
# the final flush to complete.  asyncio.TimeoutError is raised to the caller
# on expiry — the route handler must translate this to a 5xx response.
END_TIMEOUT_SECONDS: float = 10.0

# Maximum seconds stop_flusher() will wait for all in-flight workers to drain
# before cancelling stragglers and returning.  Pool disposal is safe after
# this function returns regardless of whether the timeout fired.
SHUTDOWN_TIMEOUT_SECONDS: float = 15.0

# Maximum seconds to wait for a cancelled task to acknowledge cancellation
# during the shutdown straggler-drain phase.  Bounds the second asyncio.gather
# in stop_flusher() so a non-cooperative DB driver cannot hang the process.
CANCEL_DRAIN_TIMEOUT_SECONDS: float = 3.0

# Handle to the running scheduler task — set by start_flusher().
_flush_task: asyncio.Task | None = None

# Set of ALL in-flight flush tasks: both periodic (_flush_session) and
# termination (_flush_session_final).  Tasks register on creation and
# de-register via done-callback.  stop_flusher() awaits every member
# before allowing DB pool disposal.
_flush_workers: set[asyncio.Task] = set()


class SessionStatus(str, Enum):
    CREATED = "created"
    CONNECTING = "connecting"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    EXPIRED = "expired"


@dataclass
class ConversationState:
    """Running metrics for an active session — updated by ConversationEngine."""

    health_score: int = 50
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    filler_count: int = 0
    action_items: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    objection_timeline: list = field(default_factory=list)
    buying_signal_timeline: list = field(default_factory=list)
    objections: list = field(default_factory=list)
    buying_signals: list = field(default_factory=list)
    active_alerts: list = field(default_factory=list)
    coaching_tips: list = field(default_factory=list)
    transcript_segments: list = field(default_factory=list)
    participation: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    last_silence_seconds: float = 0.0
    last_speech_time_seconds: float | None = None
    roles: dict = field(default_factory=dict)
    speaking_ratio: dict = field(default_factory=dict)
    speaker_switches: int = 0
    interruptions: int = 0
    host_speaker_id: str | None = None

    # O(1) tracking metrics
    sentiment_sum: float = 0.0
    sentiment_count: int = 0
    sentiment_processed_index: int = 0

    # Incremental processing indices (watermarks for O(1) updates)
    fillers_processed_index: int = 0
    sales_metrics_processed_index: int = 0
    meeting_metrics_processed_index: int = 0

    # Cached meeting signals for incremental OR-merge
    _meeting_signals_cache: dict = field(default_factory=dict)

    # Engine-level processing watermark (segment index into transcript_segments)
    _engine_processed_index: int = 0
    # Processed word count per segment (used to detect overlap merge growth)
    _processed_segment_word_counts: dict = field(default_factory=dict)
    # Kept for backwards compatibility with active sessions during deployment
    _boundary_word_count: int = 0


@dataclass
class SessionState:
    """Full state of an active session."""

    session_id: str
    mode: str  # "meeting" | "sales" | "interview"
    client_id: str | None
    user_id: int | None
    conversation: ConversationState = field(init=False)
    audio_buffer: AudioBuffer = field(init=False)
    status: SessionStatus = SessionStatus.CREATED
    speaker_attribution_status: str | None = None
    host_embedding: list[float] | None = None

    # WebSocket connections (one per channel per session)
    ws_audio: "WebSocket | None" = None  # receives binary audio
    ws_transcript: "WebSocket | None" = None
    ws_metrics: "WebSocket | None" = None
    ws_alerts: "WebSocket | None" = None
    ws_status: "WebSocket | None" = None

    started_at: float = field(default_factory=time.monotonic)

    # Explicit recording state tracking
    recording_started_at: float | None = None
    _accumulated_recording_duration: float = 0.0

    last_persist_at: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # ── Background flusher tracking ───────────────────────────────────────────
    # is_flushing: True while a background flush coroutine holds this session.
    # The global flush scheduler skips sessions where is_flushing is True to
    # prevent overlapping database writes on the same session.
    is_flushing: bool = False

    # Watermark: index of the next transcript_segment to flush.
    # transcript_segments is APPEND-ONLY — index arithmetic is safe here.
    # Advanced ONLY after db.commit() succeeds (deferred watermark pattern).
    last_flushed_segment_index: int = 0

    # Alert persistence: eviction-safe log + committed-ID set.
    #
    # active_alerts is a BOUNDED EVICTION WINDOW (max 3), NOT append-only.
    # An alert that is born and evicted within a single flush interval would
    # be lost if the flusher read only from active_alerts.
    #
    # alert_log: dict[alert_id, alert_dict] — grows monotonically; never
    #   evicted.  Under lock, _do_flush merges active_alerts into alert_log
    #   before computing the delta.  Any alert seen at least once at a flush
    #   boundary is permanently captured here.
    #
    # flushed_alert_ids: set of IDs already committed to the DB.
    #   Union-updated ONLY after db.commit() succeeds (deferred watermark).
    #
    # Every alert dict added to active_alerts MUST carry an "id" key
    # (UUID string) set by the alert engine.
    alert_log: dict = field(default_factory=dict)  # id → alert_dict
    flushed_alert_ids: set = field(default_factory=set)  # persisted IDs

    # Track stable segment_ids of previously persisted transcript segments
    # that were subsequently mutated by real-time speech overlap merging.
    dirty_transcript_segment_ids: set = field(default_factory=set)

    # MD5 hash of the last successfully flushed metrics snapshot.
    # A new session_metrics row is written only when the current hash differs.
    # None means metrics have never been flushed for this session.
    last_flushed_metric_hash: str | None = None

    # Handle to the in-flight final-flush task for this session.
    # Set by SessionManager.end() when it creates the final-flush task.
    # Checked on re-entry: if not done, end() reuses the existing task
    # rather than creating a second one (deduplication guard).
    _final_flush_task: "asyncio.Task | None" = field(default=None, repr=False)

    # Path to the on-disk WAV file written by AudioBuffer during the session.
    # Populated in SessionManager.end() after flush_remaining() finalises the file.
    # None for sessions where no speech audio was received.
    audio_file_path: str | None = None

    # Flag to guarantee manager.end() executes terminal logic exactly once
    # per session. Checked inside session.lock.
    _is_ending: bool = False

    # asyncio.Event for zero-overhead flush-idle signalling.
    # Contract:
    #   SET   — no periodic flush is in progress for this session.
    #   CLEAR — a periodic flush task is running (_do_flush is active).
    #
    # Transitions:
    #   _flush_loop clears it immediately BEFORE setting is_flushing=True.
    #   _do_flush sets it in EVERY exit path when clearing is_flushing:
    #     • terminal-status early return (inside lock)
    #     • nothing-to-flush early return (after lock)
    #     • finally block (normal and error paths)
    #
    # SessionManager.end() awaits this event instead of spin-polling
    # is_flushing, eliminating the previous lockless read and 50ms
    # polling granularity.
    #
    # asyncio.Event() starts UNSET.  __post_init__ sets it immediately
    # because a freshly created session has no flush in progress.
    _flush_idle: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def __post_init__(self):
        self.conversation = ConversationState()
        self.audio_buffer = AudioBuffer(_session_id=self.session_id)
        self._flush_idle.set()

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def active_recording_duration(self) -> float:
        """Returns the accumulated recording time excluding pauses."""
        duration = self._accumulated_recording_duration
        if self.recording_started_at is not None:
            duration += time.monotonic() - self.recording_started_at
        return duration


class SessionManager:
    """
    Central registry of all active sessions.

    Usage:
        mgr = get_session_manager()
        session = mgr.create(mode="meeting", user_id=1)
        mgr.get(session.session_id)
        await mgr.end(session.session_id)
    """

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    # ── Session CRUD ──────────────────────────────────────────────────────────

    def create(
        self,
        mode: str,
        user_id: int | None = None,
        client_id: str | None = None,
    ) -> SessionState:
        """Create and register a new session."""
        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            mode=mode,
            user_id=user_id,
            client_id=client_id,
            status=SessionStatus.CREATED,
        )
        # Bind the session ID to the buffer so it can name its WAV file.
        session.audio_buffer._session_id = session_id
        self._sessions[session_id] = session
        logger.info(f"Session {session_id[:8]}…: created [mode={mode}]")
        return session

    def get(self, session_id: str) -> SessionState | None:
        """Return session by ID or None."""
        return self._sessions.get(session_id)

    def get_or_raise(self, session_id: str) -> SessionState:
        """Return session or raise ValueError."""
        session = self.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        return session

    def list_active(self) -> list[SessionState]:
        """Return all sessions that are not in a terminal state."""
        terminal = {
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.INTERRUPTED,
            SessionStatus.EXPIRED,
        }
        return [s for s in self._sessions.values() if s.status not in terminal]

    async def end(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
        from_audio_handler: bool = False,
    ) -> None:
        """
        Transition session to a terminal state with zero-telemetry-loss guarantee.

        Sequence:
          1. Drain any in-flight periodic flush — bounded by END_TIMEOUT_SECONDS.
          2. Set the terminal status under session.lock.
          3. Launch the final flush as a tracked asyncio task (registered in
             _flush_workers so stop_flusher() sees it), then await it —
             also bounded by END_TIMEOUT_SECONDS.

        Raises:
            asyncio.TimeoutError: if the in-flight drain or the final flush
                does not complete within END_TIMEOUT_SECONDS.  The caller
                (route handler) MUST translate this to a 5xx response.
            Exception: any DB error raised during the final flush is propagated
                to the caller so failures are never silently swallowed.

        If start_flusher() was never called (_FLUSH_SEMAPHORE is None) the
        final flush step is skipped — intended for unit-test environments.
        """
        session = self.get(session_id)
        if session is None:
            return

        # ── Step 0: Graceful delegation ───────────────────────────────────────
        # If this was called from the REST API but the WebSocket is still active,
        # closing the WebSocket triggers the client and server to flush final
        # audio chunks. We delegate the actual end() execution to the WebSocket's
        # finally block to prevent data loss or premature pipeline execution.
        if not from_audio_handler and session.ws_audio is not None:
            async with session.lock:
                session.status = status
            try:
                # 1000 = Normal Closure
                await session.ws_audio.close(code=1000, reason="Session terminated by API")
            except Exception:
                pass
            return

        # ── Step 1: wait for any in-progress periodic flush to complete ───────
        # session._flush_idle is SET when no periodic flush is running.
        # Awaiting it is a no-op if the session is already idle; otherwise it
        # suspends until _do_flush's exit path sets the event.
        # This replaces the former spin-poll on is_flushing which read the
        # field without synchronisation and woke every 50 ms.
        await asyncio.wait_for(
            session._flush_idle.wait(),
            timeout=END_TIMEOUT_SECONDS,
        )

        # ── Step 2: transition to terminal status ─────────────────────────────
        async with session.lock:
            # RC-8 Deduplication Guard: Guarantee we only execute end() once
            if session._is_ending:
                logger.debug(
                    "Session %s…: manager.end() already in progress, skipping.",
                    session_id[:8],
                )
                return
            session._is_ending = True

            if session.recording_started_at is not None:
                session._accumulated_recording_duration += (
                    time.monotonic() - session.recording_started_at
                )
                session.recording_started_at = None
            session.status = status
        logger.info("Session %s…: ended [%s]", session_id[:8], status)

        # ── Step 3: final flush — persist remaining telemetry ─────────────────
        # Skip if start_flusher() was never called (unit-test path).
        if _FLUSH_SEMAPHORE is None:
            return

        logger.info("Session %s…: final flush started", session_id[:8])

        # Deduplication guard: if a concurrent/previous end() call already
        # created a final-flush task for this session and it is still running,
        # reuse it instead of launching a second one.  This prevents duplicate
        # DB writes when the route handler retries after a TimeoutError.
        existing = session._final_flush_task
        if existing is not None and not existing.done():
            logger.debug(
                "Session %s…: final-flush task already in-flight, reusing.",
                session_id[:8],
            )
            final_task = existing
        else:
            # Launch as a tracked task so stop_flusher() can drain it if
            # shutdown races with this call.  Store on the session so
            # concurrent end() calls can detect and reuse it.
            final_task = asyncio.create_task(
                _flush_session_final(session),
                name=f"final-flush-{session_id[:8]}",
            )
            session._final_flush_task = final_task
            _register_flush_worker(final_task)

        # Await the task (new or reused).  asyncio.shield keeps it alive in
        # _flush_workers even if wait_for times out here — stop_flusher()
        # will drain it.  Any DB exception is re-raised to the route handler.
        await asyncio.wait_for(
            asyncio.shield(final_task),
            timeout=END_TIMEOUT_SECONDS,
        )

        logger.info("Session %s…: final flush completed", session_id[:8])

        # ── Step 4: persist session status, duration, WAV path, and trigger post-
        # session diarization ─────
        try:
            from db import crud
            from db.database import AsyncSessionLocal
            from utils.profiler import profile_stage

            with profile_stage(session_id, "Session persistence"):
                async with AsyncSessionLocal() as db:
                    await crud.update_session_status(
                        db,
                        session_id,
                        status.value,
                        duration=session.active_recording_duration,
                    )
                    if status == SessionStatus.COMPLETED:
                        wav_path = session.audio_buffer.get_audio_file_path()
                        if wav_path:
                            session.audio_file_path = wav_path
                            await crud.update_session_audio_path(
                                db, session_id, wav_path
                            )
                    with profile_stage(session_id, "Database writes"):
                        await db.commit()

        except Exception:  # noqa: BLE001
            logger.exception(
                "Session %s…: failed to persist session terminal status/duration/audio_file_path",  # noqa: E501
                session_id[:8],
            )

        from core.config import get_settings

        settings = get_settings()

        if status == SessionStatus.COMPLETED and settings.enable_post_session_ai:
            try:
                logger.info(
                    "Post-session AI task scheduled",
                    extra={
                        "session_id": session_id,
                        "provider": settings.post_session_provider,
                        "enabled": True,
                    },
                )
                from services.post_session_pipeline import run_post_session_pipeline

                pipeline_task = asyncio.create_task(
                    run_post_session_pipeline(session_id),
                    name=f"post-pipeline-{session_id[:8]}",
                )
                _register_flush_worker(pipeline_task)
            except Exception as e:
                logger.error(
                    f"Failed to schedule Post-Session AI for {session_id[:8]}: {e}"
                )

        if status == SessionStatus.COMPLETED:
            # Legacy diarization has been replaced by the generative post-session AI.
            # We simply mark attribution as skipped and remove the session from memory.
            session.speaker_attribution_status = "skipped"
            logger.info(
                "Session %s…: post-session diarization skipped (legacy).",
                session_id[:8],
            )

            self.remove(session_id)
        else:
            # For non-completed sessions (failed/interrupted), finalize WAV if exists
            try:
                session.audio_buffer.flush_remaining()
            except Exception as exc:
                logger.warning(
                    "Session %s…: failed to flush remaining audio buffer — %s",
                    session_id[:8],
                    exc,
                )
            self.remove(session_id)

    async def end_all_active_sessions(self) -> None:
        """Gracefully end all active in-memory sessions on shutdown."""
        active_ids = list(self._sessions.keys())
        if not active_ids:
            logger.info("SessionManager — shutdown: no active sessions to end.")
            return

        logger.info(
            "SessionManager — shutdown: ending %d active session(s) cleanly …",
            len(active_ids),
        )

        # Await end() for all active sessions concurrently to minimize shutdown block
        tasks = []
        for sid in active_ids:
            tasks.append(self.end(sid, SessionStatus.INTERRUPTED))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("SessionManager — shutdown: all active sessions ended.")

    def remove(self, session_id: str) -> None:
        """Remove session from memory (call after DB flush)."""
        self._sessions.pop(session_id, None)

        # Fix: Clean up the stranded AlertEngine from the singleton
        from engine.conversation_engine import get_conversation_engine
        get_conversation_engine().remove_alert_engine(session_id)

    # ── Status transitions ────────────────────────────────────────────────────

    async def set_status(self, session_id: str, status: SessionStatus) -> None:
        session = self.get(session_id)
        if session:
            async with session.lock:
                session.status = status
            logger.debug(f"Session {session_id[:8]}…: → {status}")


# ── Module-level singleton ────────────────────────────────────────────────────
_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Return the global session manager singleton."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


# ── Background Flusher ────────────────────────────────────────────────────────

_TERMINAL_STATUSES = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.INTERRUPTED,
        SessionStatus.EXPIRED,
    }
)


def _compute_metric_hash(conv: ConversationState) -> str:
    """
    Compute a stable MD5 fingerprint of the current flushable metric fields.

    Metrics are serialised to a JSON string with sorted keys before hashing so
    that dict ordering differences do not generate spurious hash mismatches.
    Only fields written to session_metrics are included.

    Returns:
        Hex-digest string (32 chars).  Compared against
        session.last_flushed_metric_hash to decide whether a new row is needed.
    """
    payload = {
        "health_score": conv.health_score,
        "sentiment_score": conv.sentiment_score,
        "filler_count": conv.filler_count,
        "coaching_tips": conv.coaching_tips,
        "action_items": conv.action_items,
        "decisions": conv.decisions,
        "objection_timeline": conv.objection_timeline,
        "buying_signal_timeline": conv.buying_signal_timeline,
        "objections": conv.objections,
        "buying_signals": conv.buying_signals,
    }
    serialised = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.md5(serialised.encode()).hexdigest()


async def _do_flush(session: SessionState, *, is_final: bool = False) -> None:
    """
    Core flush implementation shared by both the periodic scheduler and the
    final-flush path triggered from SessionManager.end().

    Caller contract:
      - Periodic path: session.is_flushing is already True; caller clears it
        via the finally block here.
      - Final path (is_final=True): session is already in a terminal status;
        the terminal-status guard inside the lock is bypassed so that the
        very last telemetry is still persisted.

    Must be called with _FLUSH_SEMAPHORE already acquired by the caller
    (both paths acquire it before calling this function).
    """
    # ── 1. Snapshot delta under lock ──────────────────────────────────────────
    async with session.lock:
        # Periodic path: re-check status — session may have terminated
        # between the scheduler's is_flushing check and task execution.
        # Final path: skip this guard — termination is exactly why we're here.
        if not is_final and session.status in _TERMINAL_STATUSES:
            session.is_flushing = False
            session._flush_idle.set()  # restore idle signal — flush aborted
            return

        # ── Segments — append-only list + dirty historical segments ──────────
        seg_start = session.last_flushed_segment_index
        snapshot_len = len(session.conversation.transcript_segments)
        new_segments_count = max(0, snapshot_len - seg_start)
        dirty_ids_snap = set(session.dirty_transcript_segment_ids)
        session.dirty_transcript_segment_ids.clear()
        
        # Deep copy and strip 'words' to prevent JSON serialization errors with TranscriptWord 
        # objects during DB commit. Also cast numpy floats to python floats.
        seg_delta = []
        for i in range(snapshot_len):
            s = session.conversation.transcript_segments[i]
            s_dict = dict(s) if isinstance(s, dict) else s.__dict__.copy()
            seg_id = s_dict.get("segment_id")
            
            # Flush if it's a new segment OR if it was previously flushed but mutated
            if i >= seg_start or (seg_id and seg_id in dirty_ids_snap):
                s_dict["words"] = None
                if "start" in s_dict and s_dict["start"] is not None:
                    s_dict["start"] = float(s_dict["start"])
                if "end" in s_dict and s_dict["end"] is not None:
                    s_dict["end"] = float(s_dict["end"])
                seg_delta.append(s_dict)

        # ── Alerts ── eviction-safe: merge active_alerts into alert_log ──────────
        # active_alerts is a sliding window (max 3); alerts can be evicted
        # before the next flush tick.  alert_log is an append-only dict
        # (id → alert_dict) that grows monotonically and is never evicted.
        # By merging here (under lock), we capture every alert that has
        # appeared in the window at least once at a flush boundary.
        for a in session.conversation.active_alerts:
            aid = a.get("id")
            if aid and aid not in session.alert_log:
                session.alert_log[aid] = a
            elif not aid:
                logger.warning(
                    "Flusher — session %s: alert missing 'id' key, skipping: %r",
                    session.session_id[:8],
                    a,
                )

        # Compute delta: all log entries not yet committed to the DB.
        already_flushed = session.flushed_alert_ids
        alert_delta = [
            d for aid, d in session.alert_log.items() if aid not in already_flushed
        ]
        # Capture IDs under lock — watermark update after commit must match
        # exactly what was sent to the DB.
        alert_delta_ids = {a["id"] for a in alert_delta}

        # ── Metrics — hash-based change detection ─────────────────────────────
        current_hash = _compute_metric_hash(session.conversation)
        metrics_changed = current_hash != session.last_flushed_metric_hash

        conv = session.conversation
        metric_dicts: list[dict] = []
        if metrics_changed:
            metric_dicts = [
                {"metric_name": "health_score", "metric_value": conv.health_score},
                {
                    "metric_name": "sentiment_score",
                    "metric_value": conv.sentiment_score,
                },
                {"metric_name": "sentiment", "metric_value": conv.sentiment},
                {"metric_name": "filler_count", "metric_value": conv.filler_count},
                {"metric_name": "coaching_tips", "metric_value": conv.coaching_tips},
                {"metric_name": "action_items", "metric_value": conv.action_items},
                {"metric_name": "decisions", "metric_value": conv.decisions},
                {
                    "metric_name": "objection_timeline",
                    "metric_value": conv.objection_timeline,
                },
                {
                    "metric_name": "buying_signal_timeline",
                    "metric_value": conv.buying_signal_timeline,
                },
                {
                    "metric_name": "objections",
                    "metric_value": conv.objections,
                },
                {
                    "metric_name": "buying_signals",
                    "metric_value": conv.buying_signals,
                },
                {
                    "metric_name": "interruptions",
                    "metric_value": conv.interruptions,
                },
                {
                    "metric_name": "speaker_switches",
                    "metric_value": conv.speaker_switches,
                },
            ]
    # ── Lock released — DB IO begins ──────────────────────────────────────────

    if not seg_delta and not alert_delta and not metrics_changed:
        async with session.lock:
            session.dirty_transcript_segment_ids.update(dirty_ids_snap)
            if not is_final:
                session.is_flushing = False
                session._flush_idle.set()  # restore idle signal
        logger.debug(
            "Flusher — session %s: nothing to flush, skipping.",
            session.session_id[:8],
        )
        return

    # ── 2. Execute DB writes in one atomic transaction ────────────────────────
    try:
        from db import crud
        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            try:
                # Ensure the session row exists in DB to prevent foreign key violations
                # (e.g. if DB was reset or session was test-only)
                db_sess = await crud.get_session(db, session.session_id)
                if db_sess is None:
                    logger.warning(
                        "Flusher — session %s not found in DB. Deferring telemetry flush until route handler commits row.",
                        session.session_id[:8],
                    )
                    async with session.lock:
                        session.dirty_transcript_segment_ids.update(dirty_ids_snap)
                    return

                if seg_delta:
                    await crud.save_transcript_segments(
                        db, session.session_id, seg_delta
                    )

                if metric_dicts:
                    await crud.save_session_metrics_batch(
                        db, session.session_id, metric_dicts
                    )

                if alert_delta:
                    await crud.save_alerts_batch(db, session.session_id, alert_delta)

                # Single commit covers all three telemetry types
                await db.commit()

            except Exception:
                await db.rollback()
                async with session.lock:
                    session.dirty_transcript_segment_ids.update(dirty_ids_snap)
                raise

        # ── 3. Advance watermarks ONLY after successful commit ─────────────────
        # No lock needed here — is_flushing=True guarantees no concurrent
        # flush task is writing these fields for this session.
        session.last_flushed_segment_index += new_segments_count
        # Union-update the persisted ID set — survives any eviction that
        # occurred while the DB write was in flight.
        session.flushed_alert_ids |= alert_delta_ids
        if metrics_changed:
            session.last_flushed_metric_hash = current_hash

        logger.debug(
            "Flusher — session %s: flushed %d seg(s), %d metric(s), %d alert(s)%s.",
            session.session_id[:8],
            len(seg_delta),
            len(metric_dicts),
            len(alert_delta),
            " [final]" if is_final else "",
        )

    except Exception:  # noqa: BLE001
        # Watermarks NOT advanced — data will be retried on the next tick
        # (periodic path) or is unrecoverable (final path).
        logger.exception(
            "Flusher — session %s: DB write failed%s.",
            session.session_id[:8],
            " (final flush)" if is_final else "; will retry next cycle",
        )
        if is_final:
            # Re-raise on the final path so SessionManager.end() propagates
            # the failure to the route handler.  No silent data-loss.
            raise

    finally:
        if not is_final:
            # Clear is_flushing and unblock any end() awaiting _flush_idle.
            session.is_flushing = False
            session._flush_idle.set()


async def _flush_session(session: SessionState) -> None:
    """

    Periodic flush wrapper — acquires the throttle semaphore then delegates
    to _do_flush().  Launched as a fire-and-forget task by _flush_loop().

    The task registers itself in _flush_workers on creation and is removed
    automatically via a done-callback, allowing stop_flusher() to drain all
    in-flight workers before allowing DB pool disposal.
    """
    semaphore = _FLUSH_SEMAPHORE
    if semaphore is not None:
        async with semaphore:
            await _do_flush(session, is_final=False)


async def _flush_session_final(session: SessionState) -> None:
    """
    Final flush — persists any telemetry that arrived between the last
    periodic tick and session termination.  Called directly from
    SessionManager.end() after the session has reached a terminal status.

    Bypasses the terminal-status guard inside _do_flush so that the very
    last segment/metric/alert batch is not dropped.

    This coroutine is awaited inline (not fire-and-forget), so the caller
    blocks until the DB commit completes or fails.
    """
    semaphore = _FLUSH_SEMAPHORE
    if semaphore is not None:
        async with semaphore:
            await _do_flush(session, is_final=True)


def _register_flush_worker(task: asyncio.Task) -> None:
    """Add a flush task to the global tracking set and register auto-removal."""
    _flush_workers.add(task)
    task.add_done_callback(_flush_workers.discard)


async def _flush_loop() -> None:
    """
    Global scheduler loop — runs for the lifetime of the FastAPI process.

    Every FLUSH_INTERVAL_SECONDS:
      1. Fetches the list of non-terminal sessions from the singleton manager.
      2. Skips sessions that are already mid-flush (is_flushing=True).
      3. Sets is_flushing=True and launches an isolated _flush_session task.

    Each spawned task is registered in _flush_workers so that stop_flusher()
    can await them all before the DB pool is disposed.

    The loop itself never blocks on DB IO — each flush runs as an independent
    asyncio task.  asyncio.CancelledError is caught cleanly on shutdown.
    """
    logger.info(
        "Flusher — scheduler loop started (interval=%ss).", FLUSH_INTERVAL_SECONDS
    )
    try:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)

            manager = get_session_manager()
            active_sessions = manager.list_active()

            from ws.broadcast import broadcast_timer

            for session in active_sessions:
                # ── Heartbeat broadcast ──
                # Keep frontend timer ticking during silence
                if session.ws_metrics is not None and session.status.value == "active":
                    asyncio.create_task(
                        broadcast_timer(
                            session.ws_metrics, session.active_recording_duration
                        )
                    )

                # Skip sessions already mid-flush
                if session.is_flushing:
                    logger.debug(
                        "Flusher — session %s: already flushing, skipping.",
                        session.session_id[:8],
                    )
                    continue

                # Gate: nothing buffered — avoid creating a task at all.
                # Alerts: check both the eviction window (new alerts not yet in
                # alert_log) and alert_log entries not yet flushed.
                has_seg_delta = (
                    len(session.conversation.transcript_segments)
                    > session.last_flushed_segment_index
                )
                has_alert_delta = (
                    # New alerts in the active window not yet captured in alert_log
                    any(
                        a.get("id") and a["id"] not in session.alert_log
                        for a in session.conversation.active_alerts
                    )
                    # Or previously captured but not yet committed to DB
                    or any(
                        aid not in session.flushed_alert_ids
                        for aid in session.alert_log
                    )
                )
                current_hash = _compute_metric_hash(session.conversation)
                has_metric_delta = current_hash != session.last_flushed_metric_hash

                if not (has_seg_delta or has_alert_delta or has_metric_delta):
                    continue

                # Clear _flush_idle BEFORE setting is_flushing=True so that
                # end()'s await on _flush_idle.wait() cannot return between
                # the two assignments.  No yield point exists between these
                # two lines, so asyncio's single-thread guarantee makes this
                # atomically safe.
                session._flush_idle.clear()
                session.is_flushing = True
                task = asyncio.create_task(
                    _flush_session(session),
                    name=f"flush-{session.session_id[:8]}",
                )
                _register_flush_worker(task)

    except asyncio.CancelledError:
        logger.info("Flusher — scheduler loop cancelled (shutdown).")
        raise  # propagate so the task is marked as cancelled cleanly


def start_flusher() -> None:
    """
    Launch the global background scheduler loop as an asyncio task.

    Must be called from the FastAPI lifespan startup hook AFTER the database
    engine has been initialised (i.e., after alembic upgrade head completes).

    Also initialises _FLUSH_SEMAPHORE here (not at import time) to avoid
    event-loop mismatch errors in tests and multi-worker deployments.

    Calling this more than once is safe — a second call is a no-op if the
    existing task is still running.

    Usage in main.py:
        from ws.session_manager import start_flusher
        start_flusher()
    """
    global _flush_task, _FLUSH_SEMAPHORE
    if _flush_task is not None and not _flush_task.done():
        logger.warning("Flusher — start_flusher() called but task is already running.")
        return
    # Create the semaphore on the running event loop (not at import time).
    _FLUSH_SEMAPHORE = asyncio.Semaphore(_FLUSH_SEMAPHORE_LIMIT)
    _flush_task = asyncio.create_task(_flush_loop(), name="global-flush-scheduler")
    logger.info(
        "Flusher — background task created (semaphore limit=%d).",
        _FLUSH_SEMAPHORE_LIMIT,
    )


async def stop_flusher() -> None:
    """
    Cancel the background scheduler loop and drain ALL in-flight flush
    workers (periodic + final-flush) before returning.

    Sequence:
      1. Cancel the scheduler loop — no new tasks can be spawned after this.
      2. Await loop cancellation.
      3. Drain all registered workers via asyncio.gather, bounded by
         SHUTDOWN_TIMEOUT_SECONDS.  Workers that exceed the deadline are
         cancelled individually and their errors are logged.  The function
         always returns; DB pool disposal is safe after this call.

    Must be called from the FastAPI lifespan shutdown hook BEFORE
    engine.dispose().  Final-flush tasks started by concurrent end() calls
    are registered in _flush_workers and are therefore included in the drain.

    Usage in main.py:
        from ws.session_manager import stop_flusher
        await stop_flusher()
    """
    global _flush_task
    if _flush_task is None or _flush_task.done():
        logger.info("Flusher — stop_flusher() called but task was not running.")
    else:
        _flush_task.cancel()
        try:
            await _flush_task
        except asyncio.CancelledError:
            pass  # expected — loop exited cleanly
        _flush_task = None
        logger.info("Flusher — scheduler loop stopped.")

    # ── Primary drain ──────────────────────────────────────────────────────────
    # Drain workers visible in _flush_workers at snapshot time.  Workers
    # created by concurrent end() calls that yielded AFTER this snapshot
    # are handled by the secondary drain below.
    if _flush_workers:
        workers_snapshot = list(_flush_workers)
        logger.info(
            "Flusher — primary drain: %d worker(s) (timeout=%.1fs)…",
            len(workers_snapshot),
            SHUTDOWN_TIMEOUT_SECONDS,
        )
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*workers_snapshot, return_exceptions=True),
                timeout=SHUTDOWN_TIMEOUT_SECONDS,
            )
            for exc in results:
                if isinstance(exc, Exception) and not isinstance(
                    exc, asyncio.CancelledError
                ):
                    logger.error("Flusher — worker raised during shutdown: %s", exc)
            logger.info("Flusher — primary drain complete.")
        except asyncio.TimeoutError:
            straggler_count = sum(1 for t in workers_snapshot if not t.done())
            logger.error(
                "Flusher — primary drain exceeded %.1fs; cancelling %d straggler(s).",
                SHUTDOWN_TIMEOUT_SECONDS,
                straggler_count,
            )
            for t in workers_snapshot:
                if not t.done():
                    t.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers_snapshot, return_exceptions=True),
                    timeout=CANCEL_DRAIN_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Flusher — %d straggler(s) did not honour cancellation within %.1fs;"  # noqa: E501
                    " proceeding to secondary drain.",
                    straggler_count,
                    CANCEL_DRAIN_TIMEOUT_SECONDS,
                )

    # ── Secondary drain ────────────────────────────────────────────────────────
    # Yield once to the event loop so that any concurrent end() call whose
    # asyncio.create_task → _register_flush_worker sequence ran DURING the
    # primary gather can complete and add its task to _flush_workers before
    # we do the final check.
    #
    # Why a single sleep(0) is sufficient:
    #   _register_flush_worker() contains no await — once end() resumes from
    #   its own await (e.g. _flush_idle.wait()), it synchronously creates the
    #   task and registers it before hitting another yield.  One event-loop
    #   tick is therefore enough for all in-flight end() calls to register.
    await asyncio.sleep(0)
    if _flush_workers:
        late_workers = list(_flush_workers)
        logger.info(
            "Flusher — secondary drain: %d late worker(s) detected.",
            len(late_workers),
        )
        try:
            await asyncio.wait_for(
                asyncio.gather(*late_workers, return_exceptions=True),
                timeout=CANCEL_DRAIN_TIMEOUT_SECONDS,
            )
            logger.info("Flusher — secondary drain complete.")
        except asyncio.TimeoutError:
            logger.error(
                "Flusher — %d late worker(s) exceeded secondary drain timeout; cancelling.",  # noqa: E501
                len(late_workers),
            )
            for t in late_workers:
                if not t.done():
                    t.cancel()
            try:
                await asyncio.wait_for(
                    asyncio.gather(*late_workers, return_exceptions=True),
                    timeout=CANCEL_DRAIN_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Flusher — late workers did not honour cancellation; proceeding with disposal."  # noqa: E501
                )

    logger.info("Flusher — stopped.")
