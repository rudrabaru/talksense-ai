
import sys
import os
import logging

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.context_analyzer import analyze_sales

# Setup simplified logging
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger(__name__)

def log(msg):
    print(msg)

def create_segments(text, sentiment_label="Neutral", sentiment_score=0.0):
    return [{
        "text": text,
        "start": 0.0,
        "end": 1.0,
        "sentiment_label": sentiment_label,
        "sentiment": sentiment_score,
        "sentiment_confidence": 0.99
    }]

def verify_scenario(name, inputs, expected_quality):
    log(f"\n--- Testing Scenario: {name} ---")
    result = analyze_sales(inputs)
    
    quality = result["quality"]
    label = quality["label"]
    drivers = quality["drivers"]
    
    log(f"Input Text: {inputs[0]['text']}")
    log(f"Drivers Found: {drivers}")
    log(f"Quality Result: {label}")
    
    passed = label == expected_quality
    if passed:
        log("PASSED")
    else:
        log(f"FAILED - Expected {expected_quality}, Got {label}")
        
    return passed

def run_tests():
    tests = [
        # 1. Hard Commitment -> HIGH
        {
            "name": "Hard Commitment (Demo Booked)",
            "text": "That sounds great, I have demo booked for us next week.",
            "sentiment_label": "Positive",
            "expected": "High"
        },
        # 2. Next Step (No Hard Commitment) -> MEDIUM
        {
            "name": "Soft Next Step (Schedule Next)",
            "text": "We should schedule next steps sometime soon.",
            "sentiment_label": "Positive",
            "expected": "Medium"
        },
         # 3. Only Positive Sentiment (No concrete step) -> LOW
        {
            "name": "Positive Sentiment Only",
            "text": "I really love this product, it is amazing and wonderful.",
            "sentiment_label": "Positive", 
            "expected": "Low"
        },
        # 4. Hard Commitment override (even if sentiment wasn't super high, though usually correlated)
        {
            "name": "Hard Commitment (Calendar Invite)",
            "text": "Okay, I accepted the calendar invite.",
            "sentiment_label": "Neutral",
            "expected": "High"
        },
         # 5. Meeting on Tuesday (Hard Commitment)
        {
            "name": "Meeting on Tuesday",
            "text": "Let's do the meeting on Tuesday.",
            "sentiment_label": "Neutral",
            "expected": "High"
        }
    ]
    
    all_passed = True
    for t in tests:
        segments = create_segments(t["text"], t["sentiment_label"])
        if not verify_scenario(t["name"], segments, t["expected"]):
            all_passed = False
            
    if all_passed:
        log("\nALL SCENARIOS PASSED")
    else:
        log("\nSOME SCENARIOS FAILED")

if __name__ == "__main__":
    run_tests()
