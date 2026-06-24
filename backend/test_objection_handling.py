import asyncio
import logging
import uuid
from db.database import AsyncSessionLocal
from db import crud
from services.objection_handler import analyze_objection_handling

logging.basicConfig(level=logging.INFO)

async def test_objections():
    session_id = str(uuid.uuid4())
    
    async with AsyncSessionLocal() as db:
        # 1. Create a dummy session
        session = await crud.create_session(db, session_id=session_id, mode="sales")
        await db.commit()
        
        # 2. Add segments
        # Time 0-5: Customer objection 1 (Ignored)
        # Time 10-15: Customer objection 2 (Acknowledged) -> Sales Rep 15-18 (short)
        # Time 20-25: Customer objection 3 (Addressed) -> Sales Rep 25-35 (long, mentions keyword)
        # Time 40-45: Customer objection 4 (Resolved) -> Sales Rep 45-55 -> Customer 60-65 (Buying signal)
        
        segments = [
            # Objection 1: Too expensive (Ignored, no response within 30s)
            {"speaker_id": "Speaker 2", "start_time": 0.0, "end_time": 5.0, "text": "This is too expensive."},
            {"speaker_id": "Speaker 1", "start_time": 40.0, "end_time": 45.0, "text": "Let's pivot."},
            
            # Objection 2: Timeline (Acknowledged, < 10 words) - response at 155s
            {"speaker_id": "Speaker 2", "start_time": 150.0, "end_time": 155.0, "text": "The timeline is too short."},
            {"speaker_id": "Speaker 1", "start_time": 155.0, "end_time": 158.0, "text": "I hear you on timeline."},
            
            # Objection 3: Security (Addressed, > 10 words, contains keyword "plan") - response at 265s
            {"speaker_id": "Speaker 2", "start_time": 260.0, "end_time": 265.0, "text": "I have security concerns."},
            {"speaker_id": "Speaker 1", "start_time": 265.0, "end_time": 275.0, "text": "Our security plan is very comprehensive and we offer many features to protect your data."},
            
            # Objection 4: Features (Resolved, followed by buying signal) - response at 385s, bs at 400s
            {"speaker_id": "Speaker 2", "start_time": 380.0, "end_time": 385.0, "text": "It lacks reporting features."},
            {"speaker_id": "Speaker 1", "start_time": 385.0, "end_time": 395.0, "text": "We have an advanced reporting module coming in Q3."},
            {"speaker_id": "Speaker 2", "start_time": 400.0, "end_time": 405.0, "text": "That sounds great, I am ready to buy."},
        ]
        
        from db.models import TranscriptSegment
        for seg in segments:
            db.add(TranscriptSegment(
                session_id=uuid.UUID(session_id),
                speaker_id=seg["speaker_id"],
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"]
            ))
            
        await db.commit()
        
        # 3. Add metrics
        await crud.save_session_metrics_batch(db, session_id, [
            {
                "metric_name": "speaker_roles",
                "metric_value": {"Speaker 1": "sales_rep", "Speaker 2": "customer"}
            },
            {
                "metric_name": "objections",
                "metric_value": [
                    {"text": "This is too expensive.", "category": "Pricing", "keyword": "expensive"},
                    {"text": "The timeline is too short.", "category": "Timeline", "keyword": "timeline"},
                    {"text": "I have security concerns.", "category": "Security", "keyword": "security"},
                    {"text": "It lacks reporting features.", "category": "Features", "keyword": "features"}
                ]
            },
            {
                "metric_name": "buying_signals",
                "metric_value": [{"text": "That sounds great, I am ready to buy."}]
            }
        ])
        await db.commit()
        
        # 4. Run handler
        await analyze_objection_handling(db, session_id)
        await db.commit()
        
        # 5. Verify results
        metrics = await crud.get_latest_session_metrics(db, session_id)
        oh = next((m.metric_value for m in metrics if m.metric_name == "objection_handling"), None)
        import json
        print(json.dumps(oh, indent=2))

if __name__ == "__main__":
    asyncio.run(test_objections())
