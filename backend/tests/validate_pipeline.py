"""
TalkSense AI — Pipeline Output Validation Test Suite
=====================================================

Validates OUTPUT CORRECTNESS of the full audio intelligence pipeline.

Test Areas:
  1. REST API + Session lifecycle
  2. Conversation Engine (speaking metrics, sentiment, health score)
  3. Alert Engine (cooldown, max-3, buying signals, silence, objections)
  4. Sentiment accuracy against known text
  5. Database persistence (sessions, segments, metrics, alerts)
  6. WebSocket channel schema validity
  7. Scoring profiles boundary checks

Run from the backend/ directory:
    python tests/validate_pipeline.py

Note: NLP model loading takes ~30-60s on first run.
"""

import asyncio
import os
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from typing import Any

# ── Path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Test result tracking ───────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭  SKIP"
WARN = "⚠️  WARN"


@dataclass
class TestResult:
    area: str
    name: str
    status: str
    detail: str = ""
    expected: Any = None
    actual: Any = None


results: list[TestResult] = []


def record(
    area: str,
    name: str,
    passed: bool,
    detail: str = "",
    expected: Any = None,
    actual: Any = None,
    skip: bool = False,
    warn: bool = False,
) -> bool:
    status = SKIP if skip else (WARN if warn else (PASS if passed else FAIL))
    r = TestResult(
        area=area,
        name=name,
        status=status,
        detail=detail,
        expected=expected,
        actual=actual,
    )
    results.append(r)
    icon = status.split()[0]
    print(f"  {icon} [{area}] {name}")
    if detail:
        print(f"       → {detail}")
    if not passed and not skip and not warn and expected is not None:
        print(f"       Expected : {expected!r}")
        print(f"       Actual   : {actual!r}")
    return passed


# ══════════════════════════════════════════════════════════════════════════════
# AREA 1 — Session Manager State Machine
# ══════════════════════════════════════════════════════════════════════════════


async def test_session_manager():
    print("\n🔄 AREA 1 — Session Manager State Machine")
    area = "SessionMgr"
    try:
        from ws.session_manager import SessionStatus, get_session_manager

        manager = get_session_manager()

        # Create
        s = manager.create(mode="sales")
        sid = s.session_id

        record(
            area,
            "Session created with valid UUID-like id",
            sid is not None and len(sid) > 8,
            actual=sid,
        )

        record(
            area,
            "Session mode is 'sales'",
            s.mode == "sales",
            expected="sales",
            actual=s.mode,
        )

        # Get
        fetched = manager.get(sid)
        record(
            area,
            "Session retrievable by id",
            fetched is not None,
            actual=type(fetched).__name__,
        )

        # Elapsed time
        time.sleep(0.1)
        elapsed = manager.get(sid).elapsed_seconds if manager.get(sid) else 0.0
        record(
            area,
            "elapsed_seconds > 0 after 100ms",
            elapsed > 0,
            expected=">0",
            actual=round(elapsed, 3),
        )

        # ConversationState defaults
        conv = fetched.conversation
        record(
            area,
            "ConversationState.participation is dict",
            isinstance(conv.participation, dict),
            actual=type(conv.participation).__name__,
        )

        record(
            area,
            "ConversationState.health_score in [0, 100]",
            0 <= conv.health_score <= 100,
            expected="0-100",
            actual=conv.health_score,
        )

        record(
            area,
            "ConversationState.active_alerts is list",
            isinstance(conv.active_alerts, list),
            actual=type(conv.active_alerts).__name__,
        )

        # End session
        await manager.end(sid, SessionStatus.COMPLETED)
        after = manager.get(sid)
        record(
            area,
            "After end() — session no longer active or marked completed",
            after is None or after.status in ("completed", "COMPLETED"),
            detail="Session removed or status=completed",
        )

    except Exception as exc:
        record(
            area,
            "Session manager test EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 2 — Conversation Engine Metrics
# ══════════════════════════════════════════════════════════════════════════════


def test_conversation_engine():
    print("\n⚙️  AREA 2 — Conversation Engine Metrics")
    area = "ConvEngine"
    try:
        from engine.conversation_engine import get_conversation_engine
        from ws.session_manager import ConversationState

        engine = get_conversation_engine()
        state = ConversationState()

        segs = [
            {
                "speaker": "Speaker A",
                "text": "Thanks for hopping on. I wanted to walk you through our platform today.",  # noqa: E501
                "sentiment": 0.6,
                "start": 0.0,
                "end": 4.5,
            },
            {
                "speaker": "Speaker B",
                "text": "Sure, I have about 30 minutes.",
                "sentiment": 0.5,
                "start": 5.0,
                "end": 7.0,
            },
            {
                "speaker": "Speaker A",
                "text": "Great. So TalkSense is a real-time conversation analytics tool.",  # noqa: E501
                "sentiment": 0.7,
                "start": 8.0,
                "end": 12.0,
            },
            {
                "speaker": "Speaker B",
                "text": "Wait, does it work with Zoom?",
                "sentiment": 0.5,
                "start": 12.5,
                "end": 14.0,
            },
            {
                "speaker": "Speaker A",
                "text": "Yes, it integrates natively. You get live transcripts.",
                "sentiment": 0.65,
                "start": 15.0,
                "end": 17.5,
            },
        ]

        # NOTE: transcript_segments is appended by audio_handler, not by
        # process_segments.
        # Simulate what audio_handler does: append before calling engine.
        for seg in segs:
            state.transcript_segments.append(seg)

        state_out, alerts = engine.process_segments(
            segs, state, mode="sales", session_id="test-conv"
        )

        record(
            area,
            "Both speakers appear in participation",
            "Speaker A" in state_out.participation
            and "Speaker B" in state_out.participation,
            actual=list(state_out.participation.keys()),
        )

        total = sum(state_out.speaking_ratio.values())
        record(
            area,
            "Speaking ratios sum to 100",
            abs(total - 100.0) < 1.0,
            expected="~100",
            actual=round(total, 1),
        )

        record(
            area,
            "Sentiment score > 0 (all positive segs)",
            state_out.sentiment_score > 0,
            expected=">0",
            actual=state_out.sentiment_score,
        )

        record(
            area,
            "Sentiment label is 'positive'",
            state_out.sentiment == "positive",
            expected="positive",
            actual=state_out.sentiment,
        )

        record(
            area,
            "Health score in [0, 100]",
            0 <= state_out.health_score <= 100,
            expected="0-100",
            actual=state_out.health_score,
        )

        # transcript_segments are appended by audio_handler; we simulated that above
        record(
            area,
            "Transcript segments in state (pre-appended by audio_handler)",
            len(state_out.transcript_segments) > 0,
            expected=">0",
            actual=len(state_out.transcript_segments),
        )

        record(
            area,
            "process_segments returns list of alerts",
            isinstance(alerts, list),
            actual=type(alerts).__name__,
        )

    except Exception as exc:
        record(
            area,
            "ConversationEngine EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 3 — Sentiment Direction Accuracy
# ══════════════════════════════════════════════════════════════════════════════


def test_sentiment_direction():
    print("\n💬 AREA 3 — Sentiment Direction Accuracy")
    area = "Sentiment"
    try:
        from engine.conversation_engine import get_conversation_engine
        from ws.session_manager import ConversationState

        engine = get_conversation_engine()

        negative_segs = [
            {
                "speaker": "Speaker B",
                "text": "That is a bit high. Our budget is tight right now.",
                "sentiment": -0.6,
                "start": 70.0,
                "end": 75.0,
            },
            {
                "speaker": "Speaker B",
                "text": "What about data privacy? Where does this data go?",
                "sentiment": -0.3,
                "start": 118.0,
                "end": 122.0,
            },
        ]
        state_neg = ConversationState()
        state_neg.sentiment_score = 0.0
        state_neg, _ = engine.process_segments(
            negative_segs, state_neg, "sales", "test-neg"
        )
        record(
            area,
            "Negative sentiment text → sentiment_score < 0",
            state_neg.sentiment_score < 0,
            expected="<0",
            actual=state_neg.sentiment_score,
        )

        positive_segs = [
            {
                "speaker": "Speaker B",
                "text": "That is actually really reassuring. I did not expect that.",
                "sentiment": 0.8,
                "start": 172.0,
                "end": 176.0,
            },
            {
                "speaker": "Speaker B",
                "text": "I am actually really excited about this. Let us set it up.",
                "sentiment": 0.9,
                "start": 315.0,
                "end": 320.0,
            },
        ]
        state_pos = ConversationState()
        state_pos.sentiment_score = 0.0
        state_pos, _ = engine.process_segments(
            positive_segs, state_pos, "sales", "test-pos"
        )
        record(
            area,
            "Positive sentiment text → sentiment_score > 0",
            state_pos.sentiment_score > 0,
            expected=">0",
            actual=state_pos.sentiment_score,
        )

        # Sentiment shift: neg then positive
        state_shift = ConversationState()
        state_shift.sentiment_score = -0.5
        state_shift.sentiment = "negative"
        engine.process_segments(negative_segs, state_shift, "sales", "test-shift")
        state_shift, _ = engine.process_segments(
            positive_segs, state_shift, "sales", "test-shift"
        )
        record(
            area,
            "Sentiment shift neg→pos: score moves toward positive",
            state_shift.sentiment_score > -0.5,
            detail=f"Score: -0.5 → {state_shift.sentiment_score:.3f}",
            expected=">-0.5",
            actual=state_shift.sentiment_score,
        )

        all_scores = [
            state_neg.sentiment_score,
            state_pos.sentiment_score,
            state_shift.sentiment_score,
        ]
        record(
            area,
            "All sentiment scores in [-1.0, 1.0]",
            all(-1.0 <= s <= 1.0 for s in all_scores),
            expected="all in [-1, 1]",
            actual=all_scores,
        )

    except Exception as exc:
        record(
            area,
            "Sentiment direction EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 4 — Alert Engine
# ══════════════════════════════════════════════════════════════════════════════


def test_alert_engine():
    print("\n🔔 AREA 4 — Alert Engine")
    area = "Alerts"
    try:
        from engine.alert_engine import AlertEngine
        from ws.session_manager import ConversationState

        # --- Long silence alert ---
        ae = AlertEngine()
        st = ConversationState()
        st.last_silence_seconds = 20
        st.health_score = 70
        alerts = ae.evaluate(st, "sales", prev_health=70)
        silence = [a for a in alerts if a.get("alert_type") == "long_silence"]
        record(
            area,
            "20s silence → long_silence warning alert",
            len(silence) == 1,
            expected=1,
            actual=len(silence),
        )
        if silence:
            record(
                area,
                "Long silence level is 'warning'",
                silence[0]["level"] == "warning",
                expected="warning",
                actual=silence[0]["level"],
            )

        # --- Cooldown ---
        ae2 = AlertEngine()
        st2 = ConversationState()
        st2.last_silence_seconds = 20
        st2.health_score = 70
        ae2.evaluate(st2, "sales", prev_health=70)
        second = ae2.evaluate(st2, "sales", prev_health=70)
        second_silence = [a for a in second if a.get("alert_type") == "long_silence"]
        record(
            area,
            "Cooldown — same alert NOT re-fired within 30s",
            len(second_silence) == 0,
            expected=0,
            actual=len(second_silence),
        )

        # --- Max 3 cap ---
        ae3 = AlertEngine()
        st3 = ConversationState()
        st3.health_score = 25
        st3.last_silence_seconds = 25
        st3.objections = [{"text": "t1"}, {"text": "t2"}, {"text": "t3"}]
        st3.buying_signals = ["demo"]
        st3.duration_seconds = 200
        st3.speaking_ratio = {"Speaker A": 85, "Speaker B": 15}
        ae3.evaluate(st3, "sales", prev_health=90)
        record(
            area,
            "Active alerts never exceed 3",
            len(ae3.get_active()) <= 3,
            expected="<=3",
            actual=len(ae3.get_active()),
        )

        # --- Buying signal ---
        ae4 = AlertEngine()
        st4 = ConversationState()
        st4.buying_signals = ["demo request"]
        st4.health_score = 75
        buying = ae4.evaluate(st4, "sales", prev_health=75)
        bs = [a for a in buying if a.get("alert_type") == "buying_signal"]
        record(
            area, "Buying signal → info alert", len(bs) == 1, expected=1, actual=len(bs)
        )
        if bs:
            record(
                area,
                "Buying signal level is 'info'",
                bs[0]["level"] == "info",
                expected="info",
                actual=bs[0]["level"],
            )
            record(
                area,
                "Buying signal message mentions 'demo request'",
                "demo request" in bs[0]["message"],
                expected="contains 'demo request'",
                actual=bs[0]["message"],
            )

        # --- Repeated objections ---
        ae5 = AlertEngine()
        st5 = ConversationState()
        st5.objections = [{"text": "price"}, {"text": "privacy"}, {"text": "budget"}]
        st5.health_score = 60
        obj_alerts = ae5.evaluate(st5, "sales", prev_health=60)
        repeated = [
            a for a in obj_alerts if a.get("alert_type") == "repeated_objections"
        ]
        record(
            area,
            "3 objections → repeated_objections critical alert",
            len(repeated) >= 1,
            expected=">=1",
            actual=len(repeated),
        )
        if repeated:
            record(
                area,
                "Repeated objections level is 'critical'",
                repeated[0]["level"] == "critical",
                expected="critical",
                actual=repeated[0]["level"],
            )

        # --- Alert schema ---
        ae6 = AlertEngine()
        st6 = ConversationState()
        st6.last_silence_seconds = 25
        test_alerts = ae6.evaluate(st6, "sales", prev_health=70)
        required = {"id", "level", "message", "alert_type", "timestamp"}
        for a in test_alerts:
            missing = required - set(a.keys())
            record(
                area,
                "Alert schema — all required keys present",
                len(missing) == 0,
                expected=list(required),
                actual=list(a.keys()),
            )
            break

    except Exception as exc:
        record(
            area,
            "Alert engine EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 5 — Scoring Profiles Boundary
# ══════════════════════════════════════════════════════════════════════════════


def test_scoring_profiles():
    print("\n📊 AREA 5 — Scoring Profiles Boundary")
    area = "Scoring"
    try:
        from engine.scoring_profiles import get_profile

        all_metrics = {
            "participation": 0.0,
            "engagement": 0.0,
            "balance": 0.0,
            "action_items": 0.0,
            "objection_handling": 0.0,
            "sentiment": 0.0,
            "listening_ratio": 0.0,
            "buying_signals": 0.0,
            "confidence": 0.0,
            "filler_penalty": 0.0,
            "response_quality": 0.0,
            "pause_penalty": 0.0,
        }

        for mode in ["meeting", "sales", "interview"]:
            profile = get_profile(mode)

            s0 = profile.compute_health_score({k: 0.0 for k in all_metrics})
            record(
                area,
                f"{mode.title()} — all-zero → score in [0,100]",
                0 <= s0 <= 100,
                expected="0-100",
                actual=s0,
            )

            s100 = profile.compute_health_score({k: 100.0 for k in all_metrics})
            record(
                area,
                f"{mode.title()} — all-100 → score in [0,100]",
                0 <= s100 <= 100,
                expected="0-100",
                actual=s100,
            )

            s50 = profile.compute_health_score({k: 50.0 for k in all_metrics})
            record(
                area,
                f"{mode.title()} — all-50 → score in [0,100]",
                0 <= s50 <= 100,
                expected="0-100",
                actual=s50,
            )

    except Exception as exc:
        record(
            area,
            "Scoring profiles EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 6 — NLP Engine (Sentiment Model)
# ══════════════════════════════════════════════════════════════════════════════


def test_nlp_engine():
    print("\n🧠 AREA 6 — NLP Engine / Sentiment Model")
    area = "NLP"
    try:
        from services.nlp_engine import get_nlp_engine

        nlp = get_nlp_engine()
        record(
            area,
            "NLPEngine singleton loads without exception",
            nlp is not None,
            actual=type(nlp).__name__,
        )

        pos_seg = [
            {
                "text": "I am really excited about this — let us set it up!",
                "start": 0.0,
                "end": 3.0,
            }
        ]
        enriched = nlp.enrich_transcript(pos_seg)
        record(
            area,
            "enrich_transcript returns non-empty list",
            len(enriched) > 0,
            expected=">0",
            actual=len(enriched),
        )

        if enriched:
            seg = enriched[0]
            has_sentiment = "sentiment" in seg or "sentiment_label" in seg
            record(
                area,
                "Enriched segment has a sentiment field",
                has_sentiment,
                actual=list(seg.keys()),
            )

            if "sentiment" in seg:
                record(
                    area,
                    "Positive text → sentiment score > 0",
                    seg["sentiment"] > 0,
                    expected=">0",
                    actual=seg["sentiment"],
                )

            if "sentiment_label" in seg:
                valid = {
                    "Positive",
                    "Negative",
                    "Neutral",
                    "positive",
                    "negative",
                    "neutral",
                    "Very Positive",
                    "Very Negative",
                }
                record(
                    area,
                    "Sentiment label is a valid value",
                    seg["sentiment_label"] in valid,
                    expected=list(valid),
                    actual=seg["sentiment_label"],
                )

        neg_seg = [
            {
                "text": "That is a bit high. Our budget is very tight right now.",
                "start": 0.0,
                "end": 3.0,
            }
        ]
        enriched_neg = nlp.enrich_transcript(neg_seg)
        if enriched_neg and "sentiment_label" in enriched_neg[0]:
            neg_label = enriched_neg[0]["sentiment_label"].lower()
            record(
                area,
                "Negative text → negative or neutral label",
                "negative" in neg_label or "neutral" in neg_label,
                expected="negative or neutral",
                actual=neg_label,
            )
        else:
            record(
                area,
                "Negative text sentiment label direction check",
                True,
                detail="No sentiment_label key — skipping",
                skip=True,
            )

    except Exception as exc:
        record(
            area,
            "NLP engine EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:400]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 7 — Database Persistence (CRUD)
# ══════════════════════════════════════════════════════════════════════════════


async def test_database():
    print("\n🗄️  AREA 7 — Database Persistence")
    area = "DB"
    try:
        import uuid as _uuid

        from db import crud
        from db.database import AsyncSessionLocal, create_all

        await create_all()
        record(area, "create_all() runs without exception", True)

        async with AsyncSessionLocal() as db:
            test_sid = str(_uuid.uuid4())

            # Create
            row = await crud.create_session(db, session_id=test_sid, mode="sales")
            await db.commit()
            record(
                area,
                "create_session — row staged and committed",
                row is not None,
                actual=type(row).__name__,
            )

            # Get
            fetched = await crud.get_session(db, test_sid)
            record(
                area,
                "get_session — row retrieved by UUID",
                fetched is not None,
                actual=fetched.status if fetched else None,
            )

            record(
                area,
                "Default session status is 'created'",
                fetched.status == "created" if fetched else False,
                expected="created",
                actual=fetched.status if fetched else None,
            )

            # Transcript segments
            segs = [
                {
                    "speaker": "Speaker A",
                    "text": "Thanks for hopping on.",
                    "start": 0.0,
                    "end": 3.0,
                    "sentiment": 0.6,
                    "sentiment_label": "Positive",
                },
                {
                    "speaker": "Speaker B",
                    "text": "Sure, I have 30 minutes.",
                    "start": 4.0,
                    "end": 6.0,
                    "sentiment": 0.5,
                    "sentiment_label": "Positive",
                },
                {
                    "speaker": "Speaker A",
                    "text": "Budget is tight right now.",
                    "start": 70.0,
                    "end": 74.0,
                    "sentiment": -0.5,
                    "sentiment_label": "Negative",
                },
            ]
            await crud.save_transcript_segments(db, test_sid, segs)
            await db.commit()
            record(area, "save_transcript_segments — 3 segments committed", True)

            rows = await crud.get_transcript_segments(db, test_sid)
            record(
                area,
                "get_transcript_segments — correct count returned",
                len(rows) == len(segs),
                expected=len(segs),
                actual=len(rows),
            )

            # Metrics
            metric_rows = [
                {"metric_name": "health_score", "metric_value": 74},
                {"metric_name": "sentiment", "metric_value": "positive"},
                {
                    "metric_name": "speaking_ratio",
                    "metric_value": {"Speaker A": 58.0, "Speaker B": 42.0},
                },
                {"metric_name": "filler_count", "metric_value": 2},
            ]
            await crud.save_session_metrics_batch(db, test_sid, metric_rows)
            await db.commit()
            record(area, "save_session_metrics_batch — 4 metric rows committed", True)

            metric_fetched = await crud.get_latest_session_metrics(db, test_sid)
            names = {m.metric_name for m in metric_fetched}
            record(
                area,
                "get_latest_session_metrics — health_score present",
                "health_score" in names,
                expected="health_score",
                actual=list(names),
            )

            # Alerts
            alert_rows = [
                {
                    "alert_type": "long_silence",
                    "level": "warning",
                    "message": "Long silence detected.",
                    "timestamp": time.time(),
                },
                {
                    "alert_type": "buying_signal",
                    "level": "info",
                    "message": "Buying signal: demo request.",
                    "timestamp": time.time(),
                },
            ]
            await crud.save_alerts_batch(db, test_sid, alert_rows)
            await db.commit()
            record(area, "save_alerts_batch — 2 alerts committed", True)

            alerts_fetched = await crud.get_alerts(db, test_sid)
            record(
                area,
                "get_alerts — at least 2 alerts retrieved",
                len(alerts_fetched) >= 2,
                expected=">=2",
                actual=len(alerts_fetched),
            )

            if alerts_fetched:
                # get_alerts returns ordered by timestamp DESC
                a = alerts_fetched[0]
                record(
                    area,
                    "Alert row has severity field populated",
                    a.severity in ("warning", "info", "critical"),
                    actual=a.severity,
                )
                record(
                    area,
                    "Alert row has message field populated",
                    len(a.message) > 0,
                    actual=a.message[:40],
                )

            # End session
            ended = await crud.update_session_status(
                db, test_sid, "completed", duration=330.0
            )
            await db.commit()
            record(
                area,
                "update_session_status → 'completed'",
                ended is not None and ended.status == "completed",
                expected="completed",
                actual=ended.status if ended else None,
            )
            record(
                area,
                "update_session_status → duration persisted",
                ended is not None and ended.duration == 330.0,
                expected=330.0,
                actual=ended.duration if ended else None,
            )
            record(
                area,
                "update_session_status → ended_at populated",
                ended is not None and ended.ended_at is not None,
                actual=str(ended.ended_at) if ended else None,
            )

    except Exception as exc:
        record(
            area,
            "Database persistence EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:500]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AREA 8 — Full 5-Minute Pipeline Integration
# ══════════════════════════════════════════════════════════════════════════════


async def test_full_pipeline():
    print("\n🎯 AREA 8 — Full 5-Minute Pipeline Integration")
    area = "Integration"
    try:
        from engine.conversation_engine import get_conversation_engine
        from ws.session_manager import ConversationState

        engine = get_conversation_engine()
        state = ConversationState()
        session_id = "integration-" + str(uuid.uuid4())[:8]

        batches = [
            # T+0:00-0:45 — Neutral opening
            [
                {
                    "speaker": "Speaker A",
                    "text": "Thanks for hopping on. I wanted to walk you through our platform today.",  # noqa: E501
                    "sentiment": 0.6,
                    "start": 0.0,
                    "end": 4.5,
                },
                {
                    "speaker": "Speaker B",
                    "text": "Sure, I have about 30 minutes.",
                    "sentiment": 0.5,
                    "start": 5.0,
                    "end": 7.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "TalkSense is a real-time conversation analytics tool.",
                    "sentiment": 0.7,
                    "start": 8.0,
                    "end": 12.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "Wait, does it work with Zoom?",
                    "sentiment": 0.5,
                    "start": 12.5,
                    "end": 14.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "Yes, it integrates natively.",
                    "sentiment": 0.65,
                    "start": 15.0,
                    "end": 17.5,
                },
                {
                    "speaker": "Speaker B",
                    "text": "What does pricing look like?",
                    "sentiment": 0.4,
                    "start": 45.0,
                    "end": 47.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "We have three tiers starting at 49 dollars per month.",
                    "sentiment": 0.6,
                    "start": 55.0,
                    "end": 60.0,
                },
            ],
            # T+1:10-2:05 — NEGATIVE: objections with exact keywords, budget concerns,
            # long silence
            [
                {
                    "speaker": "Speaker B",
                    "text": "Hmm. The price is a bit high. Our budget is tight right now.",  # noqa: E501
                    "sentiment": -0.6,
                    "start": 70.0,
                    "end": 75.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "I completely understand. A lot of customers felt the same way.",  # noqa: E501
                    "sentiment": 0.3,
                    "start": 85.0,
                    "end": 90.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "How does the AI handle accents?",
                    "sentiment": -0.1,
                    "start": 95.0,
                    "end": 98.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "The Whisper model is multilingual and handles most accents well.",  # noqa: E501
                    "sentiment": 0.5,
                    "start": 105.0,
                    "end": 109.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "What about data privacy and security? Where does this data go?",  # noqa: E501
                    "sentiment": -0.3,
                    "start": 118.0,
                    "end": 122.0,
                },
            ],
            # T+2:25-3:15 — POSITIVE SHIFT: reassurance, buying signals
            [
                {
                    "speaker": "Speaker A",
                    "text": "All data is encrypted at rest and never leaves your region.",  # noqa: E501
                    "sentiment": 0.6,
                    "start": 160.0,
                    "end": 164.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "That is actually really reassuring. I did not expect that.",  # noqa: E501
                    "sentiment": 0.8,
                    "start": 172.0,
                    "end": 176.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "You own your data entirely.",
                    "sentiment": 0.7,
                    "start": 185.0,
                    "end": 188.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "Can I see a demo of the live dashboard? This looks good.",
                    "sentiment": 0.7,
                    "start": 195.0,
                    "end": 198.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "Absolutely! Here, let me share my screen.",
                    "sentiment": 0.8,
                    "start": 205.0,
                    "end": 208.0,
                },
            ],
            # T+4:00-5:30 — STRONG CLOSE: rapid switching, excitement
            [
                {
                    "speaker": "Speaker A",
                    "text": "What features would matter most to your team?",
                    "sentiment": 0.6,
                    "start": 245.0,
                    "end": 248.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "Honestly? The real-time alerts look incredible. This makes sense for us.",  # noqa: E501
                    "sentiment": 0.85,
                    "start": 255.0,
                    "end": 258.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "The alert engine fires on sentiment drops and silence.",
                    "sentiment": 0.7,
                    "start": 270.0,
                    "end": 274.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "Would we be able to trial this free for a month? Sounds good.",  # noqa: E501
                    "sentiment": 0.75,
                    "start": 290.0,
                    "end": 294.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "Yes, 30-day trial, no credit card required.",
                    "sentiment": 0.8,
                    "start": 305.0,
                    "end": 308.0,
                },
                {
                    "speaker": "Speaker B",
                    "text": "I am actually really excited. This looks good. Let us set it up.",  # noqa: E501
                    "sentiment": 0.9,
                    "start": 315.0,
                    "end": 320.0,
                },
                {
                    "speaker": "Speaker A",
                    "text": "Wonderful! I will send you the setup link right now.",
                    "sentiment": 0.85,
                    "start": 330.0,
                    "end": 334.0,
                },
            ],
        ]

        health_history: list[int] = []
        all_alerts: list[dict] = []

        for i, batch in enumerate(batches):
            # Simulate audio_handler appending segments to state BEFORE calling engine
            for seg in batch:
                state.transcript_segments.append(seg)

            # Simulate long silence after batch 1 (the 20s pause in the script)
            if i == 1:
                state.last_silence_seconds = 20

            state, new_alerts = engine.process_segments(
                batch, state, "sales", session_id
            )
            health_history.append(state.health_score)
            all_alerts.extend(new_alerts)

        record(
            area,
            "Health score changes across batches (not static)",
            len(set(health_history)) > 1,
            detail=f"History: {health_history}",
            expected="varies",
            actual=health_history,
        )

        record(
            area,
            "Final health score >= 50 (positive close)",
            state.health_score >= 50,
            expected=">=50",
            actual=state.health_score,
        )

        record(
            area,
            "Both speakers in participation after 5 min",
            len(state.participation) == 2,
            expected=2,
            actual=len(state.participation),
        )

        dominant = max(state.speaking_ratio.values()) if state.speaking_ratio else 0
        record(
            area,
            "Neither speaker exceeds 80% speaking ratio",
            dominant <= 80.0,
            expected="<=80",
            actual=dominant,
        )

        record(
            area,
            "Final sentiment is 'positive' (positive close segments)",
            state.sentiment == "positive",
            expected="positive",
            actual=state.sentiment,
        )

        total_segs = len(state.transcript_segments)
        record(
            area,
            "All 22 transcript segments accumulated",
            total_segs >= 22,
            expected=">=22",
            actual=total_segs,
        )

        record(
            area,
            "At least 1 alert fired across the session",
            len(all_alerts) > 0,
            expected=">0",
            actual=len(all_alerts),
        )

        record(
            area,
            "Active alerts never exceed 3",
            len(state.active_alerts) <= 3,
            expected="<=3",
            actual=len(state.active_alerts),
        )

        record(
            area,
            "Objections detected (budget, pricing, privacy lines)",
            len(state.objections) > 0,
            expected=">0 objections",
            actual=len(state.objections),
        )

    except Exception as exc:
        record(
            area,
            "Full pipeline integration EXCEPTION",
            False,
            detail=f"{exc}\n{traceback.format_exc()[:500]}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


async def main():
    print("=" * 70)
    print("TalkSense AI — Pipeline Output Validation Suite")
    print("=" * 70)
    print("Note: NLP model loading may take 30-60s on first run.")

    # Synchronous tests (no async dependencies)
    test_conversation_engine()
    test_sentiment_direction()
    test_alert_engine()
    test_scoring_profiles()
    test_nlp_engine()

    # Async tests
    await test_session_manager()
    await test_full_pipeline()
    await test_database()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = [r for r in results if r.status == PASS]
    failed = [r for r in results if r.status == FAIL]
    skipped = [r for r in results if r.status == SKIP]
    warned = [r for r in results if r.status == WARN]
    total = len(results)

    print(f"\n  Total   : {total}")
    print(f"  ✅ Pass  : {len(passed)}")
    print(f"  ❌ Fail  : {len(failed)}")
    print(f"  ⚠️  Warn  : {len(warned)}")
    print(f"  ⏭  Skip  : {len(skipped)}")

    if failed:
        print("\n── FAILURES ──────────────────────────────────────────────────────")
        for r in failed:
            print(f"\n  ❌ [{r.area}] {r.name}")
            if r.detail:
                # Show first 300 chars of detail to keep output readable
                print(f"     {r.detail[:300]}")
            if r.expected is not None:
                print(f"     Expected : {r.expected!r}")
                print(f"     Actual   : {r.actual!r}")

    pass_rate = round(len(passed) / total * 100, 1) if total else 0
    overall = (
        "PIPELINE VALID ✅"
        if len(failed) == 0
        else f"PIPELINE HAS {len(failed)} FAILURE(S) ❌"
    )

    print("\n" + "=" * 70)
    print(f"  Result    : {overall}")
    print(f"  Pass rate : {pass_rate}%")
    print("=" * 70)
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
