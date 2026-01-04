import logging
import sys
import os
from transformers import pipeline

# Ensure we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import KEYWORDS_CONFIG

logger = logging.getLogger(__name__)

# Keyword Dictionaries (Loaded from Config)
KEYWORDS_DB = KEYWORDS_CONFIG["nlp_enrichment"]

# Semantic Merge Configuration
CONTINUATION_STARTERS = [
    "and", "but", "so", "because", "or",
    "also", "which", "that", "with"
]

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

    def merge_semantic_segments(self, segments: list) -> list:
        """
        Merges fragmented segments based on linguistic continuity markers.
        Rule 1: Starts with continuation starter (and, but, so...)
        Rule 2: Previous segment implies continuation (no punctuation) AND needs merge.
        """
        if not segments:
            return []

        merged = []
        buffer = None

        for seg in segments:
            text = seg["text"].strip()
            if not text:
                continue

            if buffer is None:
                buffer = seg.copy() # Copy to avoid mutating original list structure if needed
                continue

            # Check Merge Criteria
            is_continuation_word = text.lower().startswith(tuple(CONTINUATION_STARTERS))
            
            prev_text = buffer["text"].strip()
            prev_ends_punct = prev_text[-1] in ['.', '?', '!'] if prev_text else False
            curr_starts_lower = text[0].islower() if text else False
            
            # Rule 1 OR Rule 2
            should_merge = is_continuation_word or (not prev_ends_punct and curr_starts_lower)

            if should_merge:
                # Merge into buffer
                buffer["text"] += " " + text
                buffer["end"] = seg["end"] # Extend time
            else:
                # Push buffer and start new
                merged.append(buffer)
                buffer = seg.copy()

        if buffer:
            merged.append(buffer)

        return merged

    def extract_keywords(self, text):
        found_keywords = []
        text_lower = text.lower()
        for category, phrases in KEYWORDS_DB.items():
            for phrase in phrases:
                if phrase in text_lower:
                    found_keywords.append(category)
                    break 
        return found_keywords

    def enrich_transcript(self, raw_segments: list) -> list:
        # 0. Semantic Merge Layer (Pre-processing)
        segments = self.merge_semantic_segments(raw_segments)
        
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
            
            # specific logic for short texts - STRICT 4 WORD GUARDRAIL
            if len(text.split()) >= 4:
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