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

    def enrich_transcript(self, segments: list) -> list:
        # 1. First pass: Keywords and prep for batch sentiment
        enriched_segments = []
        texts_to_analyze = []
        indices_to_update = []

        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            
            # Keywords (keep per-segment logic as it's regex/substring based and fast)
            keywords = self.extract_keywords(text)
            
            # Init default sentiment
            segment_data = {
                **segment,
                "keywords": keywords,
                "sentiment": 0.0,
                "sentiment_label": "Neutral",
                "sentiment_confidence": 0.0
            }
            
            # specific logic for short texts
            if len(text.split()) >= 3:
                texts_to_analyze.append(text[:512]) # Truncate for model safety
                indices_to_update.append(i)
                
            enriched_segments.append(segment_data)

        # 2. Batch Sentiment Inference
        if self.sentiment_pipeline and texts_to_analyze:
            try:
                # Run batch inference
                results = self.sentiment_pipeline(texts_to_analyze, batch_size=len(texts_to_analyze))
                
                # Map results back to segments
                for idx, result in zip(indices_to_update, results):
                    label = result["label"].lower()
                    score = result["score"]
                    
                    sentiment_score = 0.0
                    sentiment_label = "Neutral"
                    
                    if "positive" in label or "4 stars" in label or "5 stars" in label:
                        sentiment_score = score
                        sentiment_label = "Positive"
                    elif "negative" in label or "1 star" in label or "2 stars" in label:
                        sentiment_score = -score
                        sentiment_label = "Negative"
                    
                    enriched_segments[idx]["sentiment"] = round(sentiment_score, 3)
                    enriched_segments[idx]["sentiment_label"] = sentiment_label
                    enriched_segments[idx]["sentiment_confidence"] = round(score, 2)
                    
            except Exception as e:
                logger.error(f"Batch sentiment inference failed: {e}")

        return enriched_segments