"""
TalkSense AI — Session Manager

Owns the lifecycle of every active session.
Each session has:
  - A unique session_id (UUID)
  - A status (Created → Connecting → Active → Processing → Completed)
  - An AudioBuffer for accumulating PCM chunks
  - An in-memory ConversationState (metrics, alerts, transcript)
  - A reference to the broadcast WebSocket connections

Thread-safety: asyncio.Lock per session for state mutation.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from audio.buffer import AudioBuffer

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


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
    speaking_ratio: dict = field(default_factory=dict)   # {"Speaker 1": 60, "Speaker 2": 40}
    participation: dict = field(default_factory=dict)
    filler_count: int = 0
    objections: list = field(default_factory=list)
    buying_signals: list = field(default_factory=list)
    active_alerts: list = field(default_factory=list)
    transcript_segments: list = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class SessionState:
    """Full state of an active session."""
    session_id: str
    mode: str                              # "meeting" | "sales" | "interview"
    client_id: str | None
    user_id: int | None
    status: SessionStatus = SessionStatus.CREATED

    audio_buffer: AudioBuffer = field(default_factory=AudioBuffer)
    conversation: ConversationState = field(default_factory=ConversationState)

    # WebSocket connections (one per channel per session)
    ws_audio: "WebSocket | None" = None   # receives binary audio
    ws_transcript: "WebSocket | None" = None
    ws_metrics: "WebSocket | None" = None
    ws_alerts: "WebSocket | None" = None
    ws_status: "WebSocket | None" = None

    started_at: float = field(default_factory=time.monotonic)
    last_persist_at: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at


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
        terminal = {SessionStatus.COMPLETED, SessionStatus.FAILED,
                    SessionStatus.INTERRUPTED, SessionStatus.EXPIRED}
        return [s for s in self._sessions.values() if s.status not in terminal]

    async def end(self, session_id: str, status: SessionStatus = SessionStatus.COMPLETED) -> None:
        """Transition session to a terminal state."""
        session = self.get(session_id)
        if session is None:
            return
        async with session.lock:
            session.status = status
        logger.info(f"Session {session_id[:8]}…: ended [{status}]")

    def remove(self, session_id: str) -> None:
        """Remove session from memory (call after DB flush)."""
        self._sessions.pop(session_id, None)

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
