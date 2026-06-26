"""
TalkSense AI v4 — SQLAlchemy ORM Models (Phase 3)

Defines all 8 relational tables:
    users               — registered user accounts
    clients             — client profiles linked to a user
    sessions            — conversation sessions (meeting / sales / interview)
    transcript_segments — individual speaker utterances within a session
    session_metrics     — rolling metric snapshots flushed every 5 seconds
    analysis_results    — one-row final report computed on session end
    alerts              — real-time alert events raised during a session
    client_snapshots    — aggregated briefing computed after each session

Design rules (from .agent/ARCHITECTURE.md):
    - SQLAlchemy 2.x Declarative ORM style
    - All DateTime columns are timezone-aware (timezone=True)
    - All relationships use lazy="raise" to prevent implicit async IO errors
    - All child tables carry ondelete="CASCADE" foreign keys
    - All relationships carry cascade="all, delete-orphan" on the parent side
    - JSONB is used for any field that stores structured / variable-width data
    - No migration tooling (Alembic deferred) — tables are created via
      Base.metadata.create_all() inside the lifespan startup hook in main.py
"""

import uuid as _uuid_mod
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ── Declarative base ──────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Shared base for all TalkSense ORM models."""

    pass


# ── 1. users ──────────────────────────────────────────────────────────────────


class User(Base):
    """
    Registered user accounts.

    Authentication is deferred to Phase 5 (JWT + bcrypt).
    All FKs that reference users.id are nullable so Phase 3 can operate without
    a login flow.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    voice_embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # cascade omitted intentionally: clients.user_id and sessions.user_id carry
    # ondelete="SET NULL" at the DB level, so deleting a User preserves the
    # child rows and nullifies the FK. Declaring cascade="all, delete-orphan"
    # here would contradict that constraint and trigger ORM-level deletes.
    clients: Mapped[list["Client"]] = relationship(
        "Client",
        back_populates="user",
        lazy="raise",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r}>"


# ── 2. clients ────────────────────────────────────────────────────────────────


class Client(Base):
    """
    Client profiles managed by a user.

    A client represents a company / individual that participates in meetings.
    Client memory is aggregated in client_snapshots after each session.
    """

    __tablename__ = "clients"

    id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_mod.uuid4,  # ORM-level default (used by SQLAlchemy)
        server_default=func.gen_random_uuid(),  # DB-level default (used by direct SQL inserts)  # noqa: E501
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="clients",
        lazy="raise",
    )
    # cascade omitted intentionally: sessions.client_id carries ondelete="SET NULL"
    # at the DB level. ORM cascade="all, delete-orphan" would conflict with that
    # and attempt to DELETE sessions when a Client is removed via the ORM.
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="client",
        lazy="raise",
    )
    snapshots: Mapped[list["ClientSnapshot"]] = relationship(
        "ClientSnapshot",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Client id={self.id} name={self.name!r}>"


# ── 3. sessions ───────────────────────────────────────────────────────────────


class Session(Base):
    """
    A single conversation session (meeting, sales call, or interview).

    Maps 1-to-1 with a SessionState held in memory by session_manager.py.
    Status values mirror the SessionStatus enum in ws/session_manager.py:
        created | connecting | active | processing | completed | failed |
        interrupted | expired
    """

    __tablename__ = "sessions"

    id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid_mod.uuid4,  # ORM-level default (used by SQLAlchemy)
        server_default=func.gen_random_uuid(),  # DB-level default (used by direct SQL inserts)  # noqa: E501
    )
    client_id: Mapped[_uuid_mod.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,  # sessions(client_id) — listed in ARCHITECTURE.md indexes
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mode: Mapped[str] = mapped_column(
        String(50), nullable=False  # "meeting" | "sales" | "interview"
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")

    # ── Post-session speaker attribution ──────────────────────────────────────
    # Lifecycle: None (not started) → pending → processing → completed / failed
    # NULL means the pipeline has not been triggered (e.g. non-COMPLETED sessions).
    speaker_attribution_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )
    # Absolute path to the WAV file written during the live session.
    # NULL until the first speech chunk is received; set by AudioBuffer.
    audio_file_path: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="sessions",
        lazy="raise",
    )
    client: Mapped["Client | None"] = relationship(
        "Client",
        back_populates="sessions",
        lazy="raise",
    )
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="TranscriptSegment.start_time",  # always ordered by timeline
    )
    session_metrics: Mapped[list["SessionMetric"]] = relationship(
        "SessionMetric",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Alert.timestamp",
    )
    analysis_result: Mapped["AnalysisResult | None"] = relationship(
        "AnalysisResult",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,  # one-to-one
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session id={self.id} mode={self.mode!r} status={self.status!r}>"


# ── 4. transcript_segments ────────────────────────────────────────────────────


class TranscriptSegment(Base):
    """
    A single speaker utterance (one Whisper segment) within a session.

    Flushed from memory to DB every 5 seconds by the background flusher in
    ws/session_manager.py.  start_time / end_time are audio-file offsets in
    seconds, matching the payload format emitted on /ws/transcript.
    """

    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True  # e.g. "Speaker A", "Speaker B"
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        # Composite index: session lookup + ordered transcript scroll
        Index("ix_transcript_segments_session_start", "session_id", "start_time"),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="transcript_segments",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<TranscriptSegment id={self.id} "
            f"session={self.session_id} "
            f"speaker={self.speaker_id!r} "
            f"start={self.start_time}>"
        )


# ── 5. session_metrics ────────────────────────────────────────────────────────


class SessionMetric(Base):
    """
    A point-in-time metric snapshot flushed every 5 seconds.

    metric_value is JSONB to accommodate both scalar values (health_score: 88)
    and structured data (participation: {"Speaker A": 60, "Speaker B": 40}).

    Example rows for a single flush:
        metric_name="health_score",   metric_value=88
        metric_name="filler_count",   metric_value=3
        metric_name="participation",  metric_value={"Speaker A": 60, ...}
    """

    __tablename__ = "session_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[dict | list | int | float | str] = mapped_column(
        JSONB, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        # Composite index: fast metric history retrieval ordered by time
        Index("ix_session_metrics_session_ts", "session_id", "timestamp"),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="session_metrics",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SessionMetric id={self.id} "
            f"session={self.session_id} "
            f"metric={self.metric_name!r}>"
        )


# ── 6. analysis_results ───────────────────────────────────────────────────────


class AnalysisResult(Base):
    """
    Final post-session report — written exactly once when session status
    transitions to COMPLETED.

    report_json holds structured output from context_analyzer.py:
        decisions, action_items, sentiment_timeline, key_insights, summary
    This mirrors the /reports/{session_id} response schema in API_CONTRACT.md.
    """

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one-to-one with Session
        index=True,
    )
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="analysis_result",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AnalysisResult id={self.id} "
            f"session={self.session_id} "
            f"health={self.health_score}>"
        )


# ── 7. alerts ─────────────────────────────────────────────────────────────────


class Alert(Base):
    """
    Persisted alert events raised by alert_engine.py during a session.

    Severity values match the AlertEngine contract in backend_agent.md:
        "critical" | "warning" | "info"

    Alerts are broadcast on /ws/alerts and are guaranteed delivery (never
    dropped).  They are persisted here for post-session audit and client
    briefing generation.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str | None] = mapped_column(
        String(100), nullable=True  # e.g. "long_silence", "sentiment_crash"
    )
    severity: Mapped[str] = mapped_column(
        String(50), nullable=False  # "critical" | "warning" | "info"
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        # Composite index: ordered alert log per session (replaces bare session_id
        # index)
        Index("ix_alerts_session_ts", "session_id", "timestamp"),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="alerts",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Alert id={self.id} "
            f"session={self.session_id} "
            f"severity={self.severity!r} "
            f"type={self.type!r}>"
        )


# ── 8. client_snapshots ───────────────────────────────────────────────────────


class ClientSnapshot(Base):
    """
    Aggregated client briefing recomputed after every session end.

    Feeds the GET /clients/{client_id} API Contract response:
        meetings_count, sentiment_trend, common_objections, last_meeting_date

    common_objections is stored as a JSONB list so it can be queried and
    updated efficiently without string parsing.
    """

    __tablename__ = "client_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[_uuid_mod.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_trend: Mapped[str | None] = mapped_column(
        String(50), nullable=True  # "improving" | "stable" | "declining"
    )
    meetings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_meeting_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    common_objections: Mapped[list | None] = mapped_column(
        JSONB, nullable=True  # e.g. ["pricing", "integration"]
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        # Composite index: supports the .order_by(snapshot_date.desc()).limit(1)
        # query pattern in GET /clients/{client_id} — allows index-only scan
        Index("ix_client_snapshots_client_date", "client_id", "snapshot_date"),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="snapshots",
        lazy="raise",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ClientSnapshot id={self.id} "
            f"client={self.client_id} "
            f"meetings={self.meetings_count} "
            f"trend={self.sentiment_trend!r}>"
        )
