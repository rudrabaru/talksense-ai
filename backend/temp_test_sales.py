import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.context_analyzer import analyze_sales, analyze_meeting

def test_sales_mode():
    print("Testing Sales Mode...")
    
    # Mock data
    segments = [
        {"start": 10.0, "end": 20.0, "text": "Hello, how are you?", "sentiment": "Neutral", "sentiment_confidence": 0.9},
        {"start": 25.0, "end": 35.0, "text": "The price is too expensive for our budget.", "sentiment": "Negative", "sentiment_confidence": 0.95},
        {"start": 40.0, "end": 50.0, "text": "I understand your concern.", "sentiment": "Neutral", "sentiment_confidence": 0.8},
        {"start": 60.0, "end": 70.0, "text": "That sounds good actually.", "sentiment": "Positive", "sentiment_confidence": 0.85},
        {"start": 80.0, "end": 90.0, "text": "What are the next steps to proceed?", "sentiment": "Positive", "sentiment_confidence": 0.9},
    ]

    result = analyze_sales(segments)

    # Check structure
    assert result["mode"] == "sales"
    assert "summary" in result
    assert "objections" in result
    assert "buying_signals" in result
    assert "recommended_actions" in result
    assert "key_moments" in result
    assert "transcript" in result
    
    # Check Objections
    # "price", "expensive", "budget" -> Pricing objection
    assert len(result["objections"]) >= 1
    assert result["objections"][0]["type"] == "Pricing"
    
    # Check Buying Signals
    # "sounds good", "next steps", "proceed"
    assert len(result["buying_signals"]) >= 2
    
    # Check Sentiment
    # 1 Neg (confident), 2 Pos (confident) -> Overall Positive? 
    # Logic: Counts: Neg=1, Pos=2. -> Positive.
    assert result["summary"]["overall_call_sentiment"] == "positive"
    
    # Check Trend
    # First 1/3: Neutral (seg 0), Neg (seg 1 part of it? 5/3 = 1.6)
    # n=5. n//3 = 1. First = segments[:1] -> [Neutral]. Score 0.
    # Last = segments[-1:] -> [Pos]. Score 1.
    # End > Start -> Improving.
    assert result["summary"]["sentiment_trend"] == "improving"

    # Check Actions
    assert "Send pricing clarification" in result["recommended_actions"]
    assert "Send proposal" in result["recommended_actions"]

    print("Sales Mode Test Passed!")

def test_meeting_mode_integrity():
    print("Testing Meeting Mode Integrity...")
    # Just checking if it runs and returns meeting mode structure
    # Meeting mode expects different keys potentially? 
    # analyze_meeting input is nlp_input dict with "segments"
    
    segments = [
        {"start": 10.0, "end": 20.0, "text": "Let's decide on the plan.", "sentiment": "Neutral", "sentiment_confidence": 0.9, "sentiment_label": "Neutral"},
        # Note: Meeting mode uses sentiment_label in the code I saw earlier?
        # Wait, I did NOT replace analyze_meeting. It still uses sentiment_label
        # So I need to provide sentiment_label in input for meeting mode to work "correctly" logic-wise
        # The prompt said "NLP engine already enriches...".
        # If I only provide 'sentiment', Meeting Mode might break if it relies on 'sentiment_label'.
        # Let's see if analyze_meeting relies on sentiment_label.
        # Yes, line 28 in context_analyzer.py: label = seg.get("sentiment_label", "Neutral")
        # This implies the NLP engine output format described in the prompt ("sentiment": "Negative") might be INCOMPATIBLE with existing Meeting Mode if I don't fix Meeting Mode OR if the NLP engine provides BOTH.
        # The prompt says: "You must reuse this enriched data." and "You must not modify NLP outputs or Meeting Mode behavior."
        # If the existing backend expects `sentiment_label` and the prompt says the format is `sentiment`, there is a discrepancy.
        # However, the prompt says "Assume ... existing system context ... backend already has working Meeting Mode".
        # And "NLP engine already enriches ... format { ... sentiment ... }".
        # If Meeting Mode works, then either the NLP engine returns BOTH keys, OR Meeting Mode is using `sentiment` but I saw `sentiment_label`.
        # Let's double check context_analyzer.py content I read earlier.
        # Line 28: label = seg.get("sentiment_label", "Neutral")
        # Line 146: "sentiment": seg["sentiment"]
        # So Meeting Mode expects BOTH `sentiment` (for transcript) and `sentiment_label` (for logic).
        # I will assume the mock data needs both to safely test meeting mode, or that the real NLP engine provides both.
    ]
    
    data = {"segments": segments}
    result = analyze_meeting(data)
    assert result["mode"] == "meeting"
    print("Meeting Mode Integrity Test Passed!")

if __name__ == "__main__":
    test_sales_mode()
    test_meeting_mode_integrity()
