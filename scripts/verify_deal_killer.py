
import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.context_analyzer import analyze_sales

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

def verify_scenario(name, inputs, expected_quality, expected_summary_phrase=None):
    log(f"\n--- Testing Scenario: {name} ---")
    result = analyze_sales(inputs)
    
    quality = result["quality"]
    summary = result.get("summary", "")
    
    label = quality["label"]
    drivers = quality["drivers"]
    
    log(f"Input Text: {inputs[0]['text']}")
    log(f"Drivers: {drivers}")
    log(f"Quality: {label}")
    log(f"Summary: {summary}")
    
    passed = True
    if label != expected_quality:
        log(f"FAILED Quality - Expected {expected_quality}, Got {label}")
        passed = False
        
    if expected_summary_phrase and expected_summary_phrase.lower() not in summary.lower():
        log(f"FAILED Summary - Expected phrase '{expected_summary_phrase}' not found")
        passed = False
        
    if passed:
        log("PASSED")
        
    return passed

def run_tests():
    tests = [
        # 1. Pure Disqualification
        {
            "name": "Disqualification (Not switching)",
            "text": "We are not planning to switch this quarter.",
            "sentiment": "Neutral",
            "expected": "Low",
            "summary_phrase": "no plans to switch"
        },
        # 2. Pure Deferral
        {
            "name": "Deferral (Maybe later)",
            "text": "Maybe later this year properly.",
            "sentiment": "Neutral",
            "expected": "Low",
            "summary_phrase": "deferral"
        },
        # 3. Clean High (Control)
        {
            "name": "Clean High (Demo Booked)",
            "text": "That's great, let's have a demo booked for Tuesday.",
            "sentiment": "Positive",
            "expected": "High",
            "summary_phrase": "hard commitment"
        },
        # 4. CONTRADICTION (High Signal + Disqualification) -> MUST BE LOW
        {
            "name": "Contradiction (Booked but Not Switching)",
            "text": "I have a demo booked, but honestly we are not switching this quarter.",
            "sentiment": "Mixed",
            "expected": "Low", # Override must win
            "summary_phrase": "no plans to switch"
        },
        # 5. Clean Medium
        {
            "name": "Clean Medium (Soft Step)",
            "text": "We can schedule next steps soon.",
            "sentiment": "Positive", 
            "expected": "Medium",
            "summary_phrase": "soft momentum"
        }
    ]
    
    all_passed = True
    for t in tests:
        segments = create_segments(t["text"], t["sentiment"])
        if not verify_scenario(t["name"], segments, t["expected"], t.get("summary_phrase")):
            all_passed = False
            
    if all_passed:
        log("\nALL SCENARIOS PASSED")
    else:
        log("\nSOME SCENARIOS FAILED")

if __name__ == "__main__":
    run_tests()
