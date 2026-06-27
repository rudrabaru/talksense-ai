"""
TalkSense AI — Client Memory Automated Tests
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import requests

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import AsyncSessionLocal
from db.models import Client as DBClient
from db.models import Session as DBSession
from db.models import SessionMetric as DBSessionMetric
from services.client_memory import update_client_memory

BASE_URL = "http://localhost:8000"


async def test_client_memory():
    print("Initializing test client and sessions...")
    client_id = uuid.uuid4()

    # Clean up any existing test client snapshot first
    async with AsyncSessionLocal() as db:
        client = DBClient(
            id=client_id, name="Test Memory Enterprise", industry="Financial Technology"
        )
        db.add(client)
        await db.commit()

    print(
        "Asserting GET /clients/{client_id} returns default values when no snapshot exists..."  # noqa: E501
    )
    res = requests.get(f"{BASE_URL}/clients/{client_id}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["client_id"] == str(client_id)
    assert data["name"] == "Test Memory Enterprise"
    assert data["industry"] == "Financial Technology"
    assert data["meetings_count"] == 0
    assert data["sentiment_trend"] is None
    assert data["common_objections"] == []
    assert data["summary"] is None
    print("[OK] Default briefing card validated")

    # Add 1st completed session: sentiment=0.5, objections=["Pricing", "Pricing",
    # "Integration"]
    s1_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        s1 = DBSession(
            id=s1_id,
            client_id=client_id,
            mode="sales",
            status="completed",
            title="Intro Call",
            started_at=datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc),
        )
        db.add(s1)

        m1_sentiment = DBSessionMetric(
            session_id=s1_id, metric_name="sentiment_score", metric_value=0.5
        )
        m1_objections = DBSessionMetric(
            session_id=s1_id,
            metric_name="objections",
            metric_value=[
                {"type": "Pricing", "text": "Too expensive"},
                {"type": "Pricing", "text": "Cost is high"},
                {"type": "Integration", "text": "How do we integrate?"},
            ],
        )
        db.add_all([m1_sentiment, m1_objections])
        await db.commit()

    # Trigger client memory update for 1st session
    async with AsyncSessionLocal() as db:
        await update_client_memory(db, client_id)
        await db.commit()

    # Verify briefing card updates
    res = requests.get(f"{BASE_URL}/clients/{client_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["meetings_count"] == 1
    assert data["sentiment_trend"] == "stable"  # only 1 meeting
    assert set(data["common_objections"]) == {"Pricing", "Integration"}
    assert data["summary"] is not None
    assert (
        "Financial Technology" in data["summary"]
        or "Test Memory Enterprise" in data["summary"]
    )
    print("[OK] First meeting snapshot and fallback briefing validated")

    # Add 2nd completed session: sentiment=0.8 (improving), objections=["Integration"]
    s2_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        s2 = DBSession(
            id=s2_id,
            client_id=client_id,
            mode="sales",
            status="completed",
            title="Technical Demo",
            started_at=datetime(2026, 6, 21, 14, 0, 0, tzinfo=timezone.utc),
        )
        db.add(s2)

        m2_sentiment = DBSessionMetric(
            session_id=s2_id,
            metric_name="sentiment_score",
            metric_value=0.8,  # 0.8 - 0.5 = 0.3 > 0.1 -> improving
        )
        m2_objections = DBSessionMetric(
            session_id=s2_id,
            metric_name="objections",
            metric_value=[{"type": "Integration", "text": "Database sync concerns"}],
        )
        db.add_all([m2_sentiment, m2_objections])
        await db.commit()

    # Trigger client memory update for 2nd session
    async with AsyncSessionLocal() as db:
        await update_client_memory(db, client_id)
        await db.commit()

    # Verify briefing card updates for 2nd meeting
    res = requests.get(f"{BASE_URL}/clients/{client_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["meetings_count"] == 2
    assert data["sentiment_trend"] == "improving", (
        f"Expected improving, got {data['sentiment_trend']}"
    )
    assert set(data["common_objections"]) == {"Integration", "Pricing"}

    assert data["last_meeting_date"] == "2026-06-21T14:00:00+00:00"
    print(
        "[OK] Second meeting sentiment trend and objection frequency aggregation validated"  # noqa: E501
    )

    # Add 3rd completed session: sentiment=0.5 (declining), objections=["Security",
    # "Security"]
    s3_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        s3 = DBSession(
            id=s3_id,
            client_id=client_id,
            mode="sales",
            status="completed",
            title="Security Review",
            started_at=datetime(2026, 6, 22, 11, 0, 0, tzinfo=timezone.utc),
        )
        db.add(s3)

        m3_sentiment = DBSessionMetric(
            session_id=s3_id,
            metric_name="sentiment_score",
            metric_value=0.5,  # 0.5 - 0.8 = -0.3 < -0.1 -> declining
        )
        m3_objections = DBSessionMetric(
            session_id=s3_id,
            metric_name="objections",
            metric_value=[
                {"type": "Security", "text": "Data residency?"},
                {"type": "Security", "text": "SOC2 report?"},
            ],
        )
        db.add_all([m3_sentiment, m3_objections])
        await db.commit()

    # Trigger client memory update for 3rd session
    async with AsyncSessionLocal() as db:
        await update_client_memory(db, client_id)
        await db.commit()

    # Verify briefing card updates for 3rd meeting
    res = requests.get(f"{BASE_URL}/clients/{client_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["meetings_count"] == 3
    assert data["sentiment_trend"] == "declining", (
        f"Expected declining, got {data['sentiment_trend']}"
    )
    assert "Security" in data["common_objections"]
    print("[OK] Third meeting sentiment trend change (declining) validated")
    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_client_memory())
