from typing import List, Dict, Any
import math

class PatternMiner:
    def __init__(self):
        # Mock centroid for failed deals (usually loaded from ML)
        # Using a deterministic vector for simulation
        self.failed_deal_centroid = [0.1] * 384 

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot_product = sum(a*b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a*a for a in vec_a))
        norm_b = math.sqrt(sum(b*b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def mine_patterns(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        patterns_detected = []
        
        # 1. Price Concession Pattern
        # Logic: Objection (price) -> Negative Delta -> Negotiation/Discount later
        # Searching for sequence:
        # A: Segment with 'objection' flag or 'pricing' keyword AND sentiment < -0.3
        # B: Later segment with 'negotiation' keyword
        price_objection_idx = -1
        
        for i, seg in enumerate(segments):
            flags = seg.get("confidence_flags", {})
            kws = seg.get("keywords", [])
            sentiment = seg.get("sentiment", 0.0)
            
            if ("objection" in flags or "pricing" in kws) and sentiment < -0.3:
                price_objection_idx = i
                break
                
        if price_objection_idx != -1:
            # Look for negotiation AFTER objection
            for i in range(price_objection_idx + 1, len(segments)):
                seg = segments[i]
                if "negotiation" in seg.get("keywords", []):
                    patterns_detected.append("price_concession_pattern")
                    break

    
        # 2. Decision Without Ownership
        # Logic: "decision" detected -> NO "action_item" or "follow_up" detected afterwards
        decision_indices = []
        for i, seg in enumerate(segments):
            if "decision" in seg.get("confidence_flags", {}) or "decision_made" in seg.get("keywords", []):
                decision_indices.append(i)
        
        for idx in decision_indices:
            has_followup = False
            for i in range(idx + 1, len(segments)):
                kws = segments[i].get("keywords", [])
                if "action_item" in kws or "follow_up" in kws:
                    has_followup = True
                    break
            
            if not has_followup:
                patterns_detected.append("decision_without_ownership")
                break # Flag once per session is enough for summary

        return patterns_detected

    def calculate_risk_score(self, segments: List[Dict[str, Any]], patterns: List[str], topic_shifts_count: int) -> float:
        """
        Heuristic risk score (0.0 to 1.0).
        """
        risk = 0.2 # Base risk
        
        # Objections add risk
        objection_count = sum(1 for s in segments if "objection" in s.get("confidence_flags", {}))
        risk += objection_count * 0.1
        
        # Volatility risk
        sentiments = [s.get("sentiment", 0.0) for s in segments]
        if sentiments:
            import statistics
            if len(sentiments) > 1:
                volatility = statistics.stdev(sentiments)
                if volatility > 0.5: risk += 0.1
        
        # Pattern penalties
        if "decision_without_ownership" in patterns:
            risk += 0.2
        if "price_concession_pattern" in patterns:
            risk += 0.1
            
        # Topic shift instability
        if topic_shifts_count > 3:
            risk += 0.1
            
        return min(0.99, risk)

    def analyze_session(self, session_id: str, segments: List[Dict[str, Any]], main_embedding: List[float], topic_shifts: List[Dict]):
        patterns = self.mine_patterns(segments)
        risk_score = self.calculate_risk_score(segments, patterns, len(topic_shifts))
        
        # Similarity to failed deal
        similarity_to_fail = 0.0
        if main_embedding:
            similarity_to_fail = self.cosine_similarity(main_embedding, self.failed_deal_centroid)
            
        return {
            "session_id": session_id,
            "patterns_detected": patterns,
            "risk_score": round(risk_score, 2),
            "similarity_to_failed_deal": round(similarity_to_fail, 3)
        }

# Singleton
miner = PatternMiner()
