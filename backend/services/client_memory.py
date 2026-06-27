"""
TalkSense AI — Client Memory Profile Service

Automatically aggregates client metrics after session completion,
calls Gemini-2.0-flash to generate a briefing summary, and persists a
new ClientSnapshot in the database.
"""

import logging
import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from db import crud
from db.models import (
    AnalysisResult as DBAnalysisResult,
)
from db.models import (
    Client as DBClient,
)
from db.models import (
    Session as DBSession,
)
from db.models import (
    SessionMetric as DBSessionMetric,
)

logger = logging.getLogger(__name__)

BRIEFING_PROMPT = (
    "You are an CRM relationship intelligence assistant for TalkSense AI.\n"
    "\n"
    'You are given the meeting history for client "{client_name}" '
    'in the "{client_industry}" industry.\n'
    "Your goal is to write a concise, professional relationship briefing summary "
    "(2-3 sentences max) that a sales representative can read in 10 seconds "
    "before starting their next meeting with this client.\n"
    "\n"
    "The summary should highlight:\n"
    "1. The client's main concerns or interests.\n"
    "2. Sentiment trend and any unresolved objections.\n"
    "3. Crucial context from recent sessions (e.g. key focus areas, "
    "pricing discussions, or integration timelines).\n"
    "\n"
    "Here is the history of the last {num_sessions} meetings:\n"
    "{meeting_history_text}\n"
    "\n"
    "Write only the 2-3 sentence briefing summary. Do not include any greeting, "
    "intro, markdown formatting, or prefix. Be direct and actionable.\n"
)


async def update_client_memory(db: AsyncSession, client_id: uuid.UUID) -> None:
    """
    Query completed sessions and metrics for a client, calculate sentiment trend,
    aggregate common objections, generate a relationship summary using Gemini
    (or fallback), and persist a new ClientSnapshot row.
    """
    logger.info("client_memory — client %s: starting memory update", str(client_id)[:8])

    try:
        # 1. Fetch client details
        client_res = await db.execute(select(DBClient).where(DBClient.id == client_id))
        client = client_res.scalar_one_or_none()
        if not client:
            logger.error(
                "client_memory — client %s: not found in database", str(client_id)[:8]
            )
            return

        # 2. Fetch all completed sessions for this client ordered chronologically
        # (ascending)
        sessions_res = await db.execute(
            select(DBSession)
            .where(DBSession.client_id == client_id)
            .where(DBSession.status == "completed")
            .order_by(DBSession.started_at.asc())
        )
        completed_sessions = list(sessions_res.scalars().all())
        meetings_count = len(completed_sessions)

        if meetings_count == 0:
            logger.info(
                "client_memory — client %s: no completed sessions found",
                str(client_id)[:8],
            )
            return

        last_meeting_date = completed_sessions[-1].started_at

        # 3. Retrieve sentiment scores for all completed sessions
        sentiment_scores = []
        for s in completed_sessions:
            stmt = (
                select(DBSessionMetric)
                .where(DBSessionMetric.session_id == s.id)
                .where(DBSessionMetric.metric_name == "sentiment_score")
                .order_by(DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            metric = res.scalar_one_or_none()
            if metric is not None:
                val = metric.metric_value
                if isinstance(val, (int, float, str)):
                    sentiment_scores.append((s.id, float(val)))

        # 4. Calculate sentiment trend
        # Default trend: stable
        sentiment_trend = "stable"
        latest_sentiment_score = 0.0

        if sentiment_scores:
            latest_sentiment_score = sentiment_scores[-1][1]
            if len(sentiment_scores) >= 2:
                prev_sentiment_score = sentiment_scores[-2][1]
                diff = latest_sentiment_score - prev_sentiment_score
                if diff > 0.1:
                    sentiment_trend = "improving"
                elif diff < -0.1:
                    sentiment_trend = "declining"

        # 5. Aggregate common objections across all sessions
        all_objections = []
        for s in completed_sessions:
            stmt = (
                select(DBSessionMetric)
                .where(DBSessionMetric.session_id == s.id)
                .where(DBSessionMetric.metric_name == "objections")
                .order_by(DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            metric = res.scalar_one_or_none()
            if metric is not None and isinstance(metric.metric_value, list):
                for obj in metric.metric_value:
                    if isinstance(obj, dict):
                        category = obj.get("category") or obj.get("type") or "Pricing"
                    else:
                        category = str(obj)
                    all_objections.append(category)

        objection_counts = Counter(all_objections)
        common_objections = [item[0] for item in objection_counts.most_common(5)]

        # 6. Generate relationship briefing summary
        summary = None
        settings = get_settings()

        if settings.gemini_api_key:
            try:
                # Fetch last 3 sessions for detailed context
                last_three = completed_sessions[-3:]
                history_parts = []
                for i, s in enumerate(last_three):
                    # Fetch analysis result summary
                    analysis_res = await db.execute(
                        select(DBAnalysisResult).where(
                            DBAnalysisResult.session_id == s.id
                        )
                    )
                    analysis = analysis_res.scalar_one_or_none()
                    summary_text = (
                        analysis.summary if analysis else "No summary available."
                    )

                    # Fetch objection details
                    stmt = (
                        select(DBSessionMetric)
                        .where(DBSessionMetric.session_id == s.id)
                        .where(DBSessionMetric.metric_name == "objections")
                        .order_by(
                            DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc()
                        )
                        .limit(1)
                    )
                    res = await db.execute(stmt)
                    obj_metric = res.scalar_one_or_none()
                    objs = []
                    if obj_metric and isinstance(obj_metric.metric_value, list):
                        for o in obj_metric.metric_value:
                            if isinstance(o, dict):
                                objs.append(o.get("text", ""))
                            else:
                                objs.append(str(o))
                    objs_text = ", ".join(objs) if objs else "None detected"

                    # Fetch buying signals
                    stmt = (
                        select(DBSessionMetric)
                        .where(DBSessionMetric.session_id == s.id)
                        .where(DBSessionMetric.metric_name == "buying_signals")
                        .order_by(
                            DBSessionMetric.timestamp.desc(), DBSessionMetric.id.desc()
                        )
                        .limit(1)
                    )
                    res = await db.execute(stmt)
                    bs_metric = res.scalar_one_or_none()
                    bs = []
                    if bs_metric and isinstance(bs_metric.metric_value, list):
                        for b in bs_metric.metric_value:
                            if isinstance(b, dict):
                                bs.append(b.get("text", ""))
                            else:
                                bs.append(str(b))
                    bs_text = ", ".join(bs) if bs else "None detected"

                    history_parts.append(
                        f"Meeting {i + 1}:\n"
                        f"  Title: {s.title or 'Untitled Session'}\n"
                        f"  Date: "
                        f"{s.started_at.isoformat() if s.started_at else 'Unknown'}\n"
                        f"  Mode: {s.mode}\n"
                        f"  Summary: {summary_text}\n"
                        f"  Objections raised: {objs_text}\n"
                        f"  Buying signals: {bs_text}\n"
                    )

                meeting_history_text = "\n".join(history_parts)
                prompt = BRIEFING_PROMPT.format(
                    client_name=client.name,
                    client_industry=client.industry or "Unknown",
                    num_sessions=len(last_three),
                    meeting_history_text=meeting_history_text,
                )

                from typing import Any

                import google.generativeai as google_genai

                genai: Any = google_genai

                genai.configure(api_key=settings.gemini_api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")

                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=300,
                    ),
                )
                summary = response.text.strip()
                logger.info(
                    "client_memory — client %s: generated LLM summary",
                    str(client_id)[:8],
                )
            except Exception as llm_err:
                logger.error(
                    "client_memory — client %s: Gemini call failed, falling back: %s",
                    str(client_id)[:8],
                    llm_err,
                )

        if not summary:
            # Smart fallback template builder
            fallback_parts = []
            if client.industry:
                fallback_parts.append(
                    f"{client.name} is a client in the {client.industry} industry."
                )
            else:
                fallback_parts.append(
                    f"Client {client.name} has completed {meetings_count} "
                    "meeting(s) to date."
                )

            if sentiment_trend == "improving":
                fallback_parts.append(
                    "Their engagement is improving, indicating a positive outlook."
                )
            elif sentiment_trend == "declining":
                fallback_parts.append(
                    "Their engagement trend is declining, suggesting potential "
                    "concerns or unresolved issues."
                )
            else:
                fallback_parts.append("Their engagement trend is stable.")

            if common_objections:
                fallback_parts.append(
                    "Key areas of concern or discussion have focused on: "
                    f"{', '.join(common_objections).lower()}."
                )

            summary = " ".join(fallback_parts)
            logger.info(
                "client_memory — client %s: generated fallback summary",
                str(client_id)[:8],
            )

        # 7. Persist client briefing snapshot row using crud.update_client_snapshot
        await crud.update_client_snapshot(
            db=db,
            client_id=str(client_id),
            summary=summary,
            sentiment_score=latest_sentiment_score,
            sentiment_trend=sentiment_trend,
            meetings_count=meetings_count,
            last_meeting_date=last_meeting_date,
            common_objections=common_objections,
        )
        logger.info(
            "client_memory — client %s: memory update successfully staged "
            "[meetings=%d, trend=%s]",
            str(client_id)[:8],
            meetings_count,
            sentiment_trend,
        )

    except Exception as exc:
        logger.error(
            "client_memory — client %s: failed to update memory: %s",
            str(client_id)[:8],
            exc,
            exc_info=True,
        )
