from typing import Dict, Any, List

class FeatureBuilder:
    def __init__(self):
        pass

    def build_features(self, 
                       session_summary: Dict[str, Any], 
                       patterns: List[str], 
                       risk_score: float, 
                       similarity_to_failed: float) -> Dict[str, float]:
        """
        Constructs a flat feature vector (dict) from various data sources.
        All values must be numeric.
        """
        features = {}
        
        # 1. From Session Summary (Phase 2)
        features["duration_sec"] = float(session_summary.get("duration_sec", 0.0))
        features["segment_count"] = float(session_summary.get("segment_count", 0.0))
        features["avg_sentiment"] = float(session_summary.get("avg_sentiment", 0.0))
        features["sentiment_volatility"] = float(session_summary.get("sentiment_volatility", 0.0))
        
        # Flatten label counts
        # (We assume keys like 'objections', 'decisions' exist from Phase 2 log_session)
        features["objection_count"] = float(session_summary.get("objections", 0))
        features["decision_count"] = float(session_summary.get("decisions", 0))
        features["action_item_count"] = float(session_summary.get("action_items", 0))
        
        # Speaker Dominance (Simple metric: max_segments / total_segments)
        speaker_stats = session_summary.get("speaker_stats", {})
        if features["segment_count"] > 0 and speaker_stats:
            max_segs = max(speaker_stats.values())
            features["speaker_dominance_ratio"] = max_segs / features["segment_count"]
        else:
            features["speaker_dominance_ratio"] = 0.0

        # 2. From Pattern Miner (Phase 3)
        features["risk_score"] = float(risk_score)
        features["similarity_to_failed_deals"] = float(similarity_to_failed)
        
        # One-hot encode patterns (binary flags)
        features["has_decision_without_ownership"] = 1.0 if "decision_without_ownership" in patterns else 0.0
        features["has_price_concession"] = 1.0 if "price_concession_pattern" in patterns else 0.0
        
        return features

feature_builder = FeatureBuilder()
