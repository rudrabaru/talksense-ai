from typing import List, Dict, Any

class TimelineBuilder:
    def __init__(self):
        pass

    def build_markers(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        markers = []

        for i, seg in enumerate(segments):
            text = seg.get("text", "")
            sentiment = seg.get("sentiment", 0.0)
            delta = seg.get("sentiment_delta", 0.0)
            flags = seg.get("confidence_flags", {})
            kws = seg.get("keywords", [])
            
            # 1. Objection Marker
            if "objection" in flags or "pricing" in kws:
                # Only mark if sentiment is actually negative to reduce noise
                if sentiment < -0.2:
                    markers.append({
                        "type": "objection",
                        "segment_index": i,
                        "text": text[:50] + "..." if len(text) > 50 else text, # Snippet
                        "sentiment": sentiment
                    })

            # 2. Decision Marker
            if "decision" in flags or "decision_made" in kws:
                markers.append({
                    "type": "decision",
                    "segment_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })

            # 3. Sentiment Dip Marker (Visual cue)
            # Significant drop
            if delta < -0.4:
                markers.append({
                    "type": "sentiment_dip",
                    "segment_index": i,
                    "delta": delta,
                    "text": "Significant sentiment drop"
                })

        return markers

timeline_builder = TimelineBuilder()
