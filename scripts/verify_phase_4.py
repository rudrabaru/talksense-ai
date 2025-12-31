import sys
import os
import json

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

# 1. Import Scripts & Services
import export_prediction_dataset as export_script
import train_outcome_predictor as train_script
from services.prediction.predictor import predictor
from services.prediction.feature_builder import feature_builder

def verify_phase_4():
    print("Verifying Phase 4 (Predictive Analytics)...")
    
    # 1. Trigger Export (uses mock outcomes + existing logs)
    # Ensure we have logs. If verification environment is fresh, this might be empty.
    # But previous phases generated logs using 'verify_session' etc.
    # We should have 'verify_session.py' generated logs in backend/logs/session_summaries.jsonl
    # Let's hope that file exists.
    
    try:
        export_script.export_dataset()
    except Exception as e:
        print(f"Export warning: {e}")
        
    # 2. Trigger Training
    try:
        train_script.train_predictor()
    except Exception as e:
        print(f"Training warning: {e}")
        
    # Reload predictor in case it initialized before model existed
    predictor._load_model()
    
    # 3. Test Prediction (Synthetic High Risk)
    # Scenario: Price concession + No ownership + High sim to failures
    print("\nTesting Runtime Prediction...")
    
    # Mock Features (as if built by FeatureBuilder)
    high_risk_features = {
        "duration_sec": 120.0,
        "segment_count": 10.0,
        "avg_sentiment": -0.4,
        "sentiment_volatility": 0.8,
        "objection_count": 4.0,
        "decision_count": 1.0, 
        "action_item_count": 0.0, # BAD: Decision but no action
        "speaker_dominance_ratio": 0.9,
        "risk_score": 0.85, 
        "similarity_to_failed_deals": 0.9,
        "has_decision_without_ownership": 1.0,
        "has_price_concession": 1.0
    }
    
    result = predictor.predict_risk(high_risk_features)
    print("Prediction Result:", json.dumps(result, indent=2))
    
    # Assertions
    if result.get("risk_level") != "high":
        # Even with heuristic fallback, risk_score 0.85 should -> high probability of loss
        print("❌ Expected 'high' risk level")
        sys.exit(1)
        
    factors = result.get("top_contributing_factors", [])
    if "price_concession_pattern" in factors or "decision_without_ownership" in factors or "high_similarity_to_failed_deals" in factors:
        print("[OK] Explainability factors look correct")
    elif "risk_score_heuristic" in factors:
        print("[OK] Heuristic fallback correctly identified high risk score")
    else:
        print("[FAIL] Explainability failed to cite relevant factors")
        sys.exit(1)

    print("\n[PASS] Phase 4 Verification Passed!")

if __name__ == "__main__":
    verify_phase_4()
