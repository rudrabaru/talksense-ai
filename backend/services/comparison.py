"""
TalkSense AI — Session Comparison Service

Fetches persisted metric snapshots and analysis results for two sessions and
computes a structured ComparisonResult that the frontend can render directly.

Public API:
    build_comparison(db, session_id_a, session_id_b) -> dict
        Returns a ComparisonResult dict (see schema at bottom of file).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AnalysisResult as DBAnalysisResult,
)
from db.models import (
    Session as DBSession,
)
from db.models import (
    SessionMetric as DBSessionMetric,
)

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _safe_uuid(val: str) -> uuid.UUID:
    """Convert a string to UUID; raises ValueError on invalid input."""
    return uuid.UUID(str(val))


async def _fetch_session_row(db: AsyncSession, session_id: str) -> DBSession | None:
    """Return the Session ORM row or None if not found."""
    result = await db.execute(
        select(DBSession).where(DBSession.id == _safe_uuid(session_id))
    )
    return result.scalar_one_or_none()


async def _fetch_latest_metrics(db: AsyncSession, session_id: str) -> dict[str, Any]:
    """
    Return the latest value for each metric_name stored in session_metrics.

    Strategy: ORDER BY timestamp DESC and take the first occurrence of each name.
    This mirrors the pattern used in main.py's /dashboard/{session_id} endpoint.
    """
    result = await db.execute(
        select(DBSessionMetric)
        .where(DBSessionMetric.session_id == _safe_uuid(session_id))
        .order_by(DBSessionMetric.timestamp.desc())
    )
    rows = result.scalars().all()

    seen: set[str] = set()
    metrics: dict[str, Any] = {}
    for row in rows:
        if row.metric_name not in seen:
            seen.add(row.metric_name)
            metrics[row.metric_name] = row.metric_value
    return metrics


async def _fetch_analysis(db: AsyncSession, session_id: str) -> DBAnalysisResult | None:
    """Return the AnalysisResult row for the session or None."""
    result = await db.execute(
        select(DBAnalysisResult).where(
            DBAnalysisResult.session_id == _safe_uuid(session_id)
        )
    )
    return result.scalar_one_or_none()


def _extract_text_list(items: Any) -> list[str]:
    """
    Normalise a list of objections / buying-signals / action-items to plain strings.

    Items may be stored as:
        - list of strings: ["pricing", "timeline"]
        - list of dicts with a "text" key: [{"text": "pricing concern", ...}]
        - None / missing → []
    """
    if not items:
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            out.append(item.strip())
        elif isinstance(item, dict):
            text = item.get("text") or item.get("type") or item.get("message") or ""
            if text:
                out.append(str(text).strip())
    return [t for t in out if t]


def _extract_action_items(items: Any) -> list[dict]:
    """
    Normalise action_items to a list of dicts with at least a 'text' key.
    """
    if not items:
        return []
    out = []
    for item in items:
        if isinstance(item, str):
            out.append({"text": item.strip()})
        elif isinstance(item, dict):
            text = item.get("task") or item.get("text") or item.get("action") or ""
            if text:
                entry = {"text": str(text).strip()}
                if "owner" in item:
                    entry["owner"] = item["owner"]
                if "deadline" in item:
                    entry["deadline"] = item["deadline"]
                out.append(entry)
    return out


def _split_shared_unique(list_a: list[str], list_b: list[str]) -> dict:
    """
    Return {shared, unique_to_a, unique_to_b} after case-insensitive comparison.
    """
    set_a = {t.lower(): t for t in list_a}
    set_b = {t.lower(): t for t in list_b}
    shared_keys = set(set_a) & set(set_b)
    return {
        "shared": [set_a[k] for k in shared_keys],
        "unique_to_a": [v for k, v in set_a.items() if k not in shared_keys],
        "unique_to_b": [v for k, v in set_b.items() if k not in shared_keys],
    }


def _delta(val_a: Any, val_b: Any) -> float | None:
    """
    Compute val_b - val_a.  Returns None if either value is not numeric.
    Result is rounded to 2 decimal places.
    """
    try:
        return round(float(val_b) - float(val_a), 2)
    except (TypeError, ValueError):
        return None


# ── Session snapshot builder ──────────────────────────────────────────────────


async def _build_session_snapshot(
    db: AsyncSession,
    session_id: str,
) -> dict[str, Any]:
    """
    Aggregate a single session's comparison data from DB + metrics + analysis.
    Returns a flat dict consumed by build_comparison().
    """
    session_row = await _fetch_session_row(db, session_id)
    if session_row is None:
        raise ValueError(f"Session {session_id} not found")

    metrics = await _fetch_latest_metrics(db, session_id)
    analysis = await _fetch_analysis(db, session_id)

    # Pull report_json blob (may contain objections, buying_signals, action_items)
    report_json: dict = {}
    if analysis and analysis.report_json and isinstance(analysis.report_json, dict):
        report_json = analysis.report_json

    # Health score: prefer analysis_results row, fall back to session_metrics
    health_score: int | None = None
    if analysis and analysis.health_score is not None:
        health_score = analysis.health_score
    elif "health_score" in metrics:
        try:
            health_score = int(metrics["health_score"])
        except (TypeError, ValueError):
            health_score = None

    # Sentiment score
    sentiment_score: float | None = None
    for key in ("sentiment_score",):
        if key in metrics:
            try:
                sentiment_score = round(float(metrics[key]), 3)
                break
            except (TypeError, ValueError):
                pass
    if sentiment_score is None:
        ss = report_json.get("sentiment_score")
        if ss is not None:
            try:
                sentiment_score = round(float(ss), 3)
            except (TypeError, ValueError):
                pass

    # Sentiment label
    sentiment_label: str = metrics.get("sentiment") or report_json.get(
        "overall_call_sentiment", report_json.get("overall_sentiment_label", "neutral")
    )

    # Talk ratio / speaking ratio
    talk_ratio: dict = {}
    for key in ("talk_ratio_summary", "speaking_ratio", "participation"):
        val = metrics.get(key)
        if isinstance(val, dict) and val:
            talk_ratio = val
            break

    # Objections — try metrics first, then report_json
    objections_raw = metrics.get("objections") or report_json.get("objections", [])
    objection_list = _extract_text_list(objections_raw)

    # Buying signals
    signals_raw = metrics.get("buying_signals") or report_json.get("buying_signals", [])
    signal_list = _extract_text_list(signals_raw)

    # Action items / decisions
    actions_raw = (
        report_json.get("action_items") or report_json.get("recommended_actions") or []
    )
    action_list = _extract_action_items(actions_raw)

    # Duration
    duration: float | None = session_row.duration
    if duration is None and session_row.ended_at and session_row.started_at:
        duration = round(
            (session_row.ended_at - session_row.started_at).total_seconds(), 1
        )

    return {
        "session_id": str(session_row.id),
        "title": session_row.title or f"Session {str(session_row.id)[:8]}",
        "mode": session_row.mode,
        "status": session_row.status,
        "started_at": (
            session_row.started_at.isoformat() if session_row.started_at else None
        ),
        "ended_at": session_row.ended_at.isoformat() if session_row.ended_at else None,
        "duration": duration,
        "health_score": health_score,
        "sentiment_score": sentiment_score,
        "sentiment_label": str(sentiment_label) if sentiment_label else "neutral",
        "talk_ratio": talk_ratio,
        "objections": objection_list,
        "buying_signals": signal_list,
        "action_items": action_list,
        "summary": (analysis.summary if analysis else None)
        or report_json.get("summary"),
    }


# ── Public API ────────────────────────────────────────────────────────────────


async def build_comparison(
    db: AsyncSession,
    session_id_a: str,
    session_id_b: str,
) -> dict[str, Any]:
    """
    Build a full ComparisonResult for two sessions.

    Raises:
        ValueError: if either session_id does not exist in the database.

    Returns a ComparisonResult dict with the following top-level keys:
        session_a       — snapshot dict for the first session
        session_b       — snapshot dict for the second session
        delta           — numeric deltas (b - a) for health_score,
                          sentiment_score, duration
        shared_objections
        unique_to_a_objections
        unique_to_b_objections
        shared_buying_signals
        unique_to_a_buying_signals
        unique_to_b_buying_signals
        all_action_items — merged list with a "source" field ("a" | "b")
    """
    snap_a = await _build_session_snapshot(db, session_id_a)
    snap_b = await _build_session_snapshot(db, session_id_b)

    # Numeric deltas (b minus a so the UI can show improvement vs regression)
    delta = {
        "health_score": _delta(snap_a["health_score"], snap_b["health_score"]),
        "sentiment_score": _delta(snap_a["sentiment_score"], snap_b["sentiment_score"]),
        "duration": _delta(snap_a["duration"], snap_b["duration"]),
    }

    # Objection overlap
    obj_split = _split_shared_unique(snap_a["objections"], snap_b["objections"])
    # Buying signal overlap
    sig_split = _split_shared_unique(snap_a["buying_signals"], snap_b["buying_signals"])

    # Merged action items with source label
    all_action_items: list[dict] = []
    for item in snap_a["action_items"]:
        all_action_items.append({**item, "source": "a"})
    for item in snap_b["action_items"]:
        all_action_items.append({**item, "source": "b"})

    return {
        "session_a": snap_a,
        "session_b": snap_b,
        "delta": delta,
        "shared_objections": obj_split["shared"],
        "unique_to_a_objections": obj_split["unique_to_a"],
        "unique_to_b_objections": obj_split["unique_to_b"],
        "shared_buying_signals": sig_split["shared"],
        "unique_to_a_buying_signals": sig_split["unique_to_a"],
        "unique_to_b_buying_signals": sig_split["unique_to_b"],
        "all_action_items": all_action_items,
    }


# ── ComparisonResult schema (documentation) ───────────────────────────────────
# {
#   "session_a": {
#     "session_id": str,
#     "title": str,
#     "mode": "meeting" | "sales" | "interview",
#     "status": str,
#     "started_at": ISO8601,
#     "ended_at": ISO8601 | null,
#     "duration": float | null,       # seconds
#     "health_score": int | null,
#     "sentiment_score": float | null, # -1.0 to 1.0
#     "sentiment_label": str,
#     "talk_ratio": { "Speaker A": 60.0, ... },
#     "objections": [str, ...],
#     "buying_signals": [str, ...],
#     "action_items": [{ "text": str, "owner"?: str, "deadline"?: str }, ...],
#     "summary": str | null
#   },
#   "session_b": { /* same shape */ },
#   "delta": {
#     "health_score": float | null,    # positive = improvement in B
#     "sentiment_score": float | null,
#     "duration": float | null         # seconds difference
#   },
#   "shared_objections": [str, ...],
#   "unique_to_a_objections": [str, ...],
#   "unique_to_b_objections": [str, ...],
#   "shared_buying_signals": [str, ...],
#   "unique_to_a_buying_signals": [str, ...],
#   "unique_to_b_buying_signals": [str, ...],
#   "all_action_items": [
#     { "text": str, "source": "a" | "b", "owner"?: str, "deadline"?: str },
#     ...
#   ]
# }
