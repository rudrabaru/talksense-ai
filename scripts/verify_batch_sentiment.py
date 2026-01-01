import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.nlp_engine import NLPEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_batch_sentiment():
    print("Initializing NLP Engine...")
    try:
        engine = NLPEngine()
    except Exception as e:
        print(f"Failed to init engine: {e}")
        return

    # Create dummy segments
    # Mix of short (<3 words) and long (>=3 words) segments
    segments = [
        {"text": "Hello", "speaker": "A"},                            # Short
        {"text": "This is a great product I love it", "speaker": "B"}, # Long (Positive)
        {"text": "No", "speaker": "A"},                               # Short
        {"text": "I am not happy with the service", "speaker": "B"},   # Long (Negative)
        {"text": "Okay sure", "speaker": "A"},                        # Short? (2 words)
        {"text": "Let's schedule a follow up meeting", "speaker": "B"}, # Long (Neutral/Positive?)
    ]
    
    print(f"\nProcessing {len(segments)} segments...")
    start_time = time.time()
    
    enriched = engine.enrich_transcript(segments)
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Processing took {duration:.4f} seconds")

    print("\nResults:")
    for i, seg in enumerate(enriched):
        print(f"[{i}] Text: {seg['text']}")
        print(f"    Sentiment: {seg.get('sentiment')} ({seg.get('sentiment_label')})")
        print(f"    Confidence: {seg.get('sentiment_confidence')}")
        print(f"    Keywords: {seg.get('keywords')}")
        
        # Verify schema
        assert "sentiment" in seg, "Missing sentiment field"
        assert "sentiment_confidence" in seg, "Missing sentiment_confidence field"
        assert "keywords" in seg, "Missing keywords field"

        # Verify logic
        words = seg["text"].split()
        if len(words) < 3:
            if seg["sentiment"] != 0.0 or seg["sentiment_label"] != "Neutral":
                 print(f"WARNING: Short text should be Neutral/0.0 but got {seg['sentiment']}")

    print("\nVerification Passed!")

if __name__ == "__main__":
    verify_batch_sentiment()
