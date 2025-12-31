from transformers import pipeline
import torch
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize sentiment analysis pipeline (cached)
# specific model 'distilbert-base-uncased-finetuned-sst-2-english' is good for general sentiment
try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        framework="pt" # Use PyTorch
    )
    logger.info("NLP Engine: Sentiment model loaded successfully.")
except Exception as e:
    logger.error(f"NLP Engine: Failed to load sentiment model. Error: {e}")
    sentiment_pipeline = None

# Keyword Dictionaries
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

def analyze_sentiment(text):
    """
    Returns a float sentiment score between -1.0 (Negative) and 1.0 (Positive).
    """
    if not sentiment_pipeline or not text.strip():
        return 0.0
    
    try:
        # Pipeline returns list of dicts: [{'label': 'POSITIVE', 'score': 0.99}]
        result = sentiment_pipeline(text[:512])[0] # Truncate to 512 tokens for safety
        score = result['score']
        return score if result['label'] == 'POSITIVE' else -score
    except Exception as e:
        logger.warning(f"Sentiment analysis failed for text: '{text[:50]}...'. Error: {e}")
        return 0.0

def extract_keywords(text):
    """
    Finds predefined keywords in the text.
    """
    found_keywords = []
    text_lower = text.lower()
    
    for category, phrases in KEYWORDS_DB.items():
        for phrase in phrases:
            if phrase in text_lower:
                found_keywords.append(category)
                break # Dedup per category per segment
                
    return found_keywords

def enrich_transcript(transcript_data):
    """
    Enriches the Whisper transcript with sentiment and keywords.
    """
    enriched_segments = []
    
    # Process full text to get overall sentiment (optional, but good for summary)
    
    for segment in transcript_data.get("segments", []):
        text = segment.get("text", "")
        
        # 1. Calculate Sentiment
        sentiment_score = analyze_sentiment(text)
        
        # 2. Extract Keywords
        keywords = extract_keywords(text)
        
        # 3. Enrich Segment
        enriched_segment = segment.copy()
        enriched_segment["sentiment"] = round(sentiment_score, 3)
        enriched_segment["keywords"] = keywords
        
        # Mock Speaker Identification (Whisper doesn't do diarization by default without complex setup)
        # We'll just leave it as 'unknown' or implement a simple alternator if needed for UI demo
        if "speaker" not in enriched_segment:
            enriched_segment["speaker"] = "unknown"
            
        enriched_segments.append(enriched_segment)
        
    return {
        "text": transcript_data.get("text", ""),
        "segments": enriched_segments
    }
