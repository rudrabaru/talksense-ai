import os
import sys

# Add the 'backend' directory to the Python path
# This allows 'import services' to work regardless of where you run the script from
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.nlp_engine import NLPEngine

engine = NLPEngine()

test_sentences = [
    "The pricing seems a bit high for our budget",
    "That sounds good to us",
    "We will discuss internally and get back",
    "I am not sure this will work",
    "This meeting was very productive",
    "We are facing some concerns regarding timeline"
]

for text in test_sentences:
    result = engine.enrich_segment({
        "text": text,
        "start": 0.0,
        "end": 1.0
    })

    print("-" * 60)
    print("Text:", result["text"])
    print("Sentiment:", result["sentiment"])
    print("Confidence:", result["sentiment_confidence"])