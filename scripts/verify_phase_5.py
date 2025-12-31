import sys
import os
import json

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

from services.insight_composer import composer
from services.timeline_builder import timeline_builder

def verify_phase_5():
    print("Verifying Phase 5 (Insights & Explainability)...")
    
    session_id = "sess_verify_5"
    
    # 1. Mock Inputs
    # From Phase 3 (Miner)
    mock_pattern_data = {
        "patterns_detected": ["decision_without_ownership", "price_concession_pattern"],
        "risk_score": 0.82,
        "similarity_to_failed_deal": 0.75,
        "topic_shifts": [{"idx": 2}, {"idx": 5}] # minimal mock
    }
    
    # From Phase 4 (Predictor)
    mock_prediction_result = {
        "risk_probability": 0.85,
        "risk_level": "high",
        "top_contributing_factors": ["decision_without_ownership", "high_similarity_to_failed_deals"]
    }
    
    # From Phase 2 (Summary)
    mock_session_summary = {
        "duration_sec": 300
    }
    
    # Mock Segments for Timeline
    mock_segments = [
        {"text": "Hi", "sentiment": 0.0},
        {"text": "Price is too high", "sentiment": -0.6, "keywords": ["pricing"], "sentiment_delta": -0.6},
        {"text": "Okay we will buy", "sentiment": 0.8, "keywords": ["decision_made"], "sentiment_delta": 0.4}
    ]
    
    # 2. Run Insight Composer
    insight_obj = composer.compose_insight_object(
        session_id,
        mock_pattern_data,
        mock_prediction_result,
        mock_session_summary
    )
    
    print("\n[Insights Object]")
    print(json.dumps(insight_obj, indent=2))
    
    # 3. Run Timeline Builder
    markers = timeline_builder.build_markers(mock_segments)
    
    print("\n[Timeline Markers]")
    print(json.dumps(markers, indent=2))
    
    # 4. Assertions
    # Check Explainability
    insights = insight_obj["key_insights"]
    if not any("decision was made, but no clear next action" in ins for ins in insights):
        print("[FAIL] Explanation for 'decision_without_ownership' missing")
        sys.exit(1)
        
    # Check Attention
    attn = insight_obj["attention_signal"]
    if attn["level"] != "high":
        print(f"[FAIL] Expected 'high' attention, got {attn['level']}")
        sys.exit(1)
        
    # Check Timeline
    if len(markers) != 3:
         print(f"[FAIL] Expected 3 markers (Objection + Dip + Decision), got {len(markers)}")
         sys.exit(1)
         
    types = [m["type"] for m in markers]
    if "objection" not in types or "decision" not in types or "sentiment_dip" not in types:
         print("[FAIL] Missing marker types")
         sys.exit(1)

    print("\n[PASS] Phase 5 Verification Passed!")

if __name__ == "__main__":
    verify_phase_5()
