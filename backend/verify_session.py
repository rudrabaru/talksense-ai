import sys
import os
import json
from datetime import datetime

# Add backend to path so we can import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.logger import log_session, SESSION_LOG_FILE

def verify_session():
    # 1. Define dummy session data
    session_id = "sess_" + datetime.now().strftime("%Y%m%d%H%M%S")
    mode = "sales"
    duration_sec = 125.5
    segment_count = 10
    avg_sentiment = -0.15
    min_sentiment = -0.6
    sentiment_volatility = 0.3
    label_counts = {"objection": 2, "follow_up": 1}
    speaker_stats = {"spk_0": 9, "spk_1": 1}

    # 2. Log it
    log_session(
        session_id=session_id,
        mode=mode,
        duration_sec=duration_sec,
        segment_count=segment_count,
        avg_sentiment=avg_sentiment,
        min_sentiment=min_sentiment,
        sentiment_volatility=sentiment_volatility,
        label_counts=label_counts,
        speaker_stats=speaker_stats
    )

    # 3. Read back
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", SESSION_LOG_FILE)
    
    with open(log_file, "r") as f:
        lines = f.readlines()
        # Find our specific session
        found = False
        for line in reversed(lines):
            data = json.loads(line)
            if data.get("session_id") == session_id:
                found = True
                break
        
    if not found:
        print("❌ Session log entry not found")
        sys.exit(1)

    print("Logged Session Data:", json.dumps(data, indent=2))

    # 4. Assertions
    errors = []
    
    # Check flattened fields (Task 3)
    if data.get("action_items") is None:
         errors.append("❌ action_items missing")
    if data.get("objections") != 2:
         errors.append(f"❌ objections count mismatch: expected 2, got {data.get('objections')}")
    if data.get("follow_ups") != 1:
         errors.append(f"❌ follow_ups count mismatch: expected 1, got {data.get('follow_ups')}")

    if data.get("duration_sec") != duration_sec:
         errors.append("❌ duration_sec mismatch")
    if data.get("label_counts") != label_counts:
         errors.append("❌ label_counts mismatch")
    if data.get("speaker_stats") != speaker_stats:
         errors.append("❌ speaker_stats mismatch")
    if "rule_version" not in data:
         errors.append("❌ rule_version missing")
    if "created_at" not in data:
         errors.append("❌ created_at missing")

    if errors:
        print("\nERRORS FOUND:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\n[PASS] Session Logging Verification Passed!")

if __name__ == "__main__":
    verify_session()
