import asyncio
import os
import sys
import traceback
import uuid

import requests

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import AsyncSessionLocal
from db.models import Client as DBClient
from db.models import Session as DBSession
from db.models import SessionMetric as DBSessionMetric

BASE_URL = "http://localhost:8000"


async def test_all():
    print("Initializing test data...")
    # 1. Create clients
    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()
    s_ids = [uuid.uuid4() for _ in range(5)]

    async with AsyncSessionLocal() as db:
        c1 = DBClient(id=c1_id, name="Test Client Alpha", industry="Tech")
        db.add(c1)
        c2 = DBClient(id=c2_id, name="Test Client Beta", industry="Health")
        db.add(c2)

        # S1: meeting, completed, alpha, duration=300
        s1 = DBSession(
            id=s_ids[0],
            mode="meeting",
            status="completed",
            title="Alpha Project Alignment",
            client_id=c1_id,
            duration=300.0,
        )
        db.add(s1)

        # S2: sales, active, beta, duration=None
        s2 = DBSession(
            id=s_ids[1],
            mode="sales",
            status="active",
            title="Beta Product Pitch",
            client_id=c2_id,
        )
        db.add(s2)

        # S3: interview, failed, no client, duration=500
        s3 = DBSession(
            id=s_ids[2],
            mode="interview",
            status="failed",
            title="Python Engineer Interview",
            duration=500.0,
        )
        db.add(s3)

        # S4: sales, completed, alpha, duration=1500
        s4 = DBSession(
            id=s_ids[3],
            mode="sales",
            status="completed",
            title="Alpha Contract Review",
            client_id=c1_id,
            duration=1500.0,
        )
        db.add(s4)

        # S5: meeting, interrupted, beta, duration=100
        s5 = DBSession(
            id=s_ids[4],
            mode="meeting",
            status="interrupted",
            title="Beta Retro Sprint",
            client_id=c2_id,
            duration=100.0,
        )
        db.add(s5)

        # S1 has health=75 then health=85 (latest). Sentiment=positive.
        m1_h1 = DBSessionMetric(
            session_id=s_ids[0], metric_name="health_score", metric_value=75
        )
        m1_h2 = DBSessionMetric(
            session_id=s_ids[0], metric_name="health_score", metric_value=85
        )
        m1_s = DBSessionMetric(
            session_id=s_ids[0], metric_name="sentiment", metric_value="positive"
        )

        # S4 has health=95. Sentiment=neutral.
        m4_h = DBSessionMetric(
            session_id=s_ids[3], metric_name="health_score", metric_value=95
        )
        m4_s = DBSessionMetric(
            session_id=s_ids[3], metric_name="sentiment", metric_value="neutral"
        )

        db.add_all([m1_h1, m1_h2, m1_s, m4_h, m4_s])
        await db.commit()

    print("Running HTTP API assertions...")
    try:
        # Test 1: List all sessions
        res = requests.get(f"{BASE_URL}/sessions")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["total"] >= 5, f"Expected total >= 5, got {data['total']}"
        items = data["items"]
        s1_item = [i for i in items if i["session_id"] == str(s_ids[0])][0]
        assert s1_item["mode"] == "meeting"
        assert s1_item["status"] == "completed"
        assert s1_item["client_name"] == "Test Client Alpha"
        assert s1_item["health_score"] == 85, (
            f"Expected latest health score 85, got {s1_item['health_score']}"
        )
        assert s1_item["sentiment"] == "positive"
        print("[OK] Baseline list & DTO verified")

        # Test 2: Filter by status
        res = requests.get(f"{BASE_URL}/sessions?status=active")
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["status"] == "active"
        print("[OK] Status filtering verified")

        # Test 3: Filter by mode
        res = requests.get(f"{BASE_URL}/sessions?mode=interview")
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["mode"] == "interview"
        print("[OK] Mode filtering verified")

        # Test 4: Search
        res = requests.get(f"{BASE_URL}/sessions?search=Alignment")
        assert res.status_code == 200
        titles = [i["title"] for i in res.json()["items"]]
        assert any("Alignment" in t for t in titles)
        print("[OK] Title search verified")

        # Test 5: Search by client name
        res = requests.get(f"{BASE_URL}/sessions?search=Beta")
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert "Beta" in (item["title"] or "") or "Beta" in (
                item["client_name"] or ""
            )
        print("[OK] Client name search verified")

        # Test 6: Sort by duration
        res = requests.get(f"{BASE_URL}/sessions?sort_by=duration&sort_order=desc")
        assert res.status_code == 200
        durations = [
            i["duration"] for i in res.json()["items"] if i["duration"] is not None
        ]
        assert durations == sorted(durations, reverse=True)
        print("[OK] Sorting verified")

        # Test 7: Pagination
        res = requests.get(f"{BASE_URL}/sessions?limit=2&page=1")
        assert res.status_code == 200
        d = res.json()
        assert len(d["items"]) <= 2
        assert d["page"] == 1
        assert d["limit"] == 2
        print("[OK] Pagination verified")

        print("[PASS] ALL TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        print(f"[FAIL] TEST FAILURE: {e}")
        traceback.print_exc()
        raise e

    finally:
        print("Cleaning up test data...")
        from sqlalchemy import delete

        async with AsyncSessionLocal() as db:
            for sid in s_ids:
                await db.execute(delete(DBSession).where(DBSession.id == sid))
            await db.execute(delete(DBClient).where(DBClient.id.in_([c1_id, c2_id])))
            await db.commit()
        # Dispose engine to close all connections cleanly
        # await engine.dispose()
        print("Cleanup done.")


if __name__ == "__main__":
    asyncio.run(test_all())
