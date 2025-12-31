import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

# Keyword Dictionaries (Restored)
KEYWORDS_DB = {
    # Meeting Mode Keywords
    "action_item": ["action item", "to do", "take ownership", "i will do", "responsible for"],
    "decision_made": ["decision", "decided", "agreed", "consensus", "conclusion"],
    "blocker": ["blocked", "stuck", "dependency", "waiting for", "issue"],
    "timeline_risk": ["deadline", "late", "delay", "push back", "risk"],
    
    # Sales Mode Keywords
    "price_objection": ["too expensive", "price", "budget", "cost", "discount"],
    "negotiation": ["negotiate", "offer", "deal", "contract", "terms"],
    "competitor": ["competitor", "other vendor", "using", "switched to"],
    "follow_up": ["follow up", "next steps", "circle back", "schedule", "calendar"],
    "positive_signal": ["great", "perfect", "good fit", "interested", "exactly what we need"]
}

class NLPEngine:
    def __init__(self):
        try:
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="tabularisai/multilingual-sentiment-analysis"
            )
            logger.info("NLP Engine: Sentiment model loaded successfully.")
        except Exception as e:
            logger.error(f"NLP Engine: Failed to load sentiment model (Offline?). Error: {e}")
            self.sentiment_pipeline = None

    def extract_keywords(self, text):
        found_keywords = []
        text_lower = text.lower()
        for category, phrases in KEYWORDS_DB.items():
            for phrase in phrases:
                if phrase in text_lower:
                    found_keywords.append(category)
                    break 
        return found_keywords

    def enrich_segment(self, segment: dict) -> dict:
        text = segment.get("text", "")
        
        # 1. Keywords
        keywords = self.extract_keywords(text)

        # 2. Sentiment
        sentiment_score = 0.0
        sentiment_label = "Neutral"
        sentiment_confidence = 0.0
        
        if self.sentiment_pipeline:
            try:
                # Handle short text
                if len(text.split()) >= 3:
                     result = self.sentiment_pipeline(text[:512])[0]
                     label = result["label"].lower() # e.g. "5 stars", "positive", "label_1"
                     score = result["score"]
                     sentiment_confidence = score
                     
                     # Simple heuristic mapping for multilingual model
                     if "positive" in label or "4 stars" in label or "5 stars" in label:
                         sentiment_score = score
                         sentiment_label = "Positive"
                     elif "negative" in label or "1 star" in label or "2 stars" in label:
                         sentiment_score = -score
                         sentiment_label = "Negative"
                     else:
                         sentiment_score = 0.0
                         sentiment_label = "Neutral"
            except Exception as e:
                logger.warning(f"Sentiment inference failed: {e}")

        return {
            **segment,
            "keywords": keywords,
            "sentiment": round(sentiment_score, 3), # Float for Sales Mode
            "sentiment_label": sentiment_label,      # String for Meeting Mode
            "sentiment_confidence": round(sentiment_confidence, 2) # Actual confidence
        }

    def enrich_transcript(self, segments: list) -> list:
        return [self.enrich_segment(s) for s in segments]