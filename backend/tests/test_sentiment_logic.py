import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.context_analyzer import calculate_business_sentiment, adjust_segment_sentiment

def test_business_sentiment():
    print("Testing Business Sentiment Logic...\n")

    # 1. Test Segment Adjustment
    # Case A: "bug" (Execution) - Raw Negative
    text_a = "We found a critical bug in production."
    raw_a = -0.9
    adj_a = adjust_segment_sentiment(text_a, raw_a)
    print(f"Case A (Bug Only): Raw={raw_a} -> Adj={adj_a}")
    assert adj_a > raw_a # Should be less negative (downweighted)
    assert adj_a == raw_a * 0.3 # Check exact math: -0.27

    # Case B: "bug" + "fixed" (Resolution)
    text_b = "We found a bug but it is fixed now."
    raw_b = -0.5 # Model might still hate "bug"
    adj_b = adjust_segment_sentiment(text_b, raw_b)
    print(f"Case B (Bug + Fixed): Raw={raw_b} -> Adj={adj_b}")
    assert adj_b >= 0.0 # Should flip to non-negative

    # 2. Test End State Boost
    segments_boost = [
        {"text": "Bad start.", "sentiment_score": -0.8},
        {"text": "No blockers.", "sentiment_score": 0.0}, # Boost trigger
        {"text": "Good to go.", "sentiment_score": 0.2}    # Boost trigger
    ]
    # Avg raw ~ -0.2. Boost +0.3. Final ~ +0.1.
    score_boost, label_boost = calculate_business_sentiment(segments_boost, "uncertain")
    print(f"End Boost Test: Score={score_boost}, Label={label_boost}")
    assert score_boost > -0.2 # Boost applied
    
    # 3. Test Outcome Override
    # Scenario: Meeting Health is GOOD, but text is strictly negative
    segments_neg = [
        {"text": "We hate this.", "sentiment_score": -0.9},
        {"text": "Terrible.", "sentiment_score": -0.9}
    ]
    # Without override, this is Tense.
    # With override (Health="good"):
    score_ovr, label_ovr = calculate_business_sentiment(segments_neg, "good")
    print(f"Outcome Override Test: Health=good, RawAvg=-0.9 -> FinalLabel={label_ovr}")
    assert label_ovr == "Neutral / Focused" # Should be neutralized
    assert score_ovr == 0.0

    print("\nBusiness Sentiment Tests Passed!")

if __name__ == "__main__":
    test_business_sentiment()
