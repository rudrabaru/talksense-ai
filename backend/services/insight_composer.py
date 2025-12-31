from typing import Dict, Any, List

# Phase 5.2 - Explainability Mappings
EXPLANATIONS = {
    "decision_without_ownership": 
        "A decision was made, but no clear next action or owner was assigned.",
    "price_concession_pattern":
        "Pricing objections were followed by negotiation, which often indicates pressure.",
    "high_similarity_to_failed_deals":
        "This conversation is similar to past deals that did not close.",
    "multiple_objections":
        "Multiple distinct objections were raised, indicating significant resistance.",
    "risk_score_heuristic":
        "Combination of sentiment volatility and objections resulted in a high risk score."
}

class InsightComposer:
    def __init__(self):
        pass

    def get_explanation(self, key: str) -> str:
        return EXPLANATIONS.get(key, f"Factor detected: {key.replace('_', ' ')}.")

    def calculate_attention_level(self, risk_probability: float, patterns: List[str]) -> Dict[str, Any]:
        """
        Determines if this session needs Low, Medium, or High attention.
        Not 'Action', but 'Attention'.
        """
        level = "low"
        reasons = []

        # High Risk
        if risk_probability > 0.6:
            level = "high"
            reasons.append("High predicted risk of deal loss")
        elif risk_probability > 0.3:
            level = "medium"
        
        # Pattern Severity
        if "decision_without_ownership" in patterns:
            if level == "low": level = "medium"
            reasons.append("Process Gap: Decision without ownership")
            
        if "price_concession_pattern" in patterns:
            if level == "low": level = "medium"
            reasons.append("Negotiation Pressure: Early price concession")

        return {
            "level": level,
            "reasons": reasons
        }

    def compose_insight_object(self, 
                               session_id: str, 
                               pattern_data: Dict[str, Any], 
                               prediction_result: Dict[str, Any],
                               session_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        The ONE object the frontend consumes.
        """
        
        # 1. Prediction Data
        risk_prob = prediction_result.get("risk_probability", 0.0)
        risk_level = prediction_result.get("risk_level", "unknown")
        factors = prediction_result.get("top_contributing_factors", [])

        # 2. Key Insights (Human Readable from Factors + Patterns)
        key_insights = []
        # Add prediction factors with explanations
        for f in factors:
            key_insights.append(self.get_explanation(f))
            
        # Add pattern specific insights if not covered by factors
        patterns = pattern_data.get("patterns_detected", [])
        for p in patterns:
            explanation = self.get_explanation(p)
            if explanation not in key_insights:
                key_insights.append(explanation)

        # 3. Attention Signal
        attention = self.calculate_attention_level(risk_prob, patterns)

        # 4. Guardrails & Limitations
        guardrails = {
            "confidence": "medium", # Static for now, could be dynamic based on model confidence
            "limitations": [
                "Prediction based on limited historical data",
                "Patterns inferred from conversation structure",
                "Automated insights require human verification"
            ]
        }
        
        # 5. Supporting Evidence (Raw data for drill-down)
        evidence = {
            "patterns_detected": patterns,
            "topic_shifts": len(pattern_data.get("topic_shifts", [])), # If passed in pattern_data
            "risk_score_raw": pattern_data.get("risk_score", 0.0),
            "similarity_to_failed": pattern_data.get("similarity_to_failed_deal", 0.0)
        }

        # FINAL OBJECT
        return {
            "session_id": session_id,
            "risk_level": risk_level,
            "risk_probability": risk_prob,
            "attention_signal": attention,
            "key_insights": key_insights,
            "supporting_evidence": evidence,
            "guardrails": guardrails
        }

# Singleton
composer = InsightComposer()
