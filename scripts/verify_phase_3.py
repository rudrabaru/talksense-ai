import sys
import os
import json
import logging

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

# Import Phase 3 services
from services.embeddings.embed_conversation import embedder
from services.pattern_miner import miner

def verify_phase_3():
    print("Running Phase 3 Verification (Offline Analysis)...")
    
    # 1. Create Dummy Enriched Session
    # Scenario: Decision made -> No follow up (decision_without_ownership)
    # Scenario: Price objection -> Negotiation (price_concession_pattern)
    session_id = "sess_phase3_verify"
    
    segments = [
        {
            "text": "We really like the product.",
            "sentiment": 0.5,
            "speaker_id": "spk_1",
            "keywords": []
        },
        {
            "text": "However, the price is way too high for our budget.",
            "sentiment": -0.5,
            "speaker_id": "spk_1",
            "keywords": ["pricing"], # Maps to objection
            "confidence_flags": {"objection": "high"}
        },
        {
            "text": "I understand. Let me see if we can apply a discount.",
            "sentiment": 0.2,
            "speaker_id": "spk_0",
            "keywords": ["negotiation"] # Trigger price_concession
        },
        {
            "text": "Okay, we have decided to move forward.",
            "sentiment": 0.8,
            "speaker_id": "spk_1",
            "keywords": ["decision_made"]
        },
        {
            "text": "Great, thanks for the call. Bye.",
            "sentiment": 0.2,
            "speaker_id": "spk_0",
            "keywords": [] # No action item/follow up here -> decision_without_ownership
        }
    ]
    
    # 2. Run Embeddings (Phase 3.1)
    print("Step 1: Generating Embeddings...")
    embedding_result = embedder.process_session(session_id, segments)
    
    # Verify Embedding Structure
    if len(embedding_result["conversation_embedding"]) == 0:
        print("❌ Conversation embedding empty")
        sys.exit(1)
    if len(embedding_result["speaker_embeddings"]) != 2:
        print("❌ Speaker embeddings count check failed")
        sys.exit(1)
        
    print(f"[OK] Embeddings generated. Window count: {len(embedding_result['window_embeddings'])}")
    
    # 3. Run Pattern Mining (Phase 3.2)
    print("Step 2: Mining Patterns...")
    mining_result = miner.analyze_session(
        session_id, 
        segments, 
        embedding_result["conversation_embedding"], 
        embedding_result["topic_shifts"]
    )
    
    patterns = mining_result["patterns_detected"]
    print("Detected Patterns:", patterns)
    print(f"Risk Score: {mining_result['risk_score']}")
    
    # Verify Patterns
    if "decision_without_ownership" not in patterns:
        print("❌ Failed to detect 'decision_without_ownership' pattern")
        sys.exit(1)
    if "price_concession_pattern" not in patterns:
        print("❌ Failed to detect 'price_concession_pattern'")
        sys.exit(1)
        
    print("\n[PASS] Phase 3 Verification Passed!")

if __name__ == "__main__":
    verify_phase_3()
