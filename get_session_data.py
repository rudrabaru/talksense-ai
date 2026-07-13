import asyncio
import json
from sqlalchemy import select
from backend.db.database import get_db, SessionLocal
from backend.db.models import Session, TranscriptSegment, SessionMetric

async def main():
    session_id = 'ef14a466-4117-4137-8048-88222b9a14e8'
    async with SessionLocal() as db:
        # Get transcripts
        res = await db.execute(
            select(TranscriptSegment)
            .where(TranscriptSegment.session_id == session_id)
            .order_by(TranscriptSegment.start_time)
        )
        segments = res.scalars().all()
        print("--- POST-SESSION TRANSCRIPTS ---")
        print(f"Total: {len(segments)}")
        for s in segments:
            print(f"[{s.start_time:.2f}-{s.end_time:.2f}] {s.speaker}: {s.text}")

        # Get metrics to see live transcripts
        res = await db.execute(
            select(SessionMetric)
            .where(SessionMetric.session_id == session_id)
            .where(SessionMetric.metric_name == 'transcripts')
            .order_by(SessionMetric.timestamp)
        )
        metrics = res.scalars().all()
        print("\n--- LIVE TRANSCRIPT METRICS ---")
        for m in metrics:
            print(f"Timestamp: {m.timestamp}")
            for item in m.metric_value:
                print(f"  {item}")

if __name__ == "__main__":
    asyncio.run(main())
