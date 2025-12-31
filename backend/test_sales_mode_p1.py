from services.context_analyzer import analyze_sales

def test_sales_logic():
    print("Testing Sales Mode Part 1 Logic...")
    
    # 1. Test Overall Sentiment: Mixed
    # Logic: If Pos > 0 and Neg > 0 -> Mixed
    segments_mixed = [
        {"text": "Bad", "start": 0.0, "end": 2.0, "sentiment": "Negative", "sentiment_confidence": 0.9},
        {"text": "Good", "start": 3.0, "end": 4.0, "sentiment": "Positive", "sentiment_confidence": 0.9},
        {"text": "Neutral", "start": 5.0, "end": 6.0, "sentiment": "Neutral", "sentiment_confidence": 0.9}
    ]
    result = analyze_sales(segments_mixed)
    print(f"Mixed Test Result: {result['summary']['overall_call_sentiment']}")
    if result["summary"]["overall_call_sentiment"] != "mixed":
        print("FAIL: Expected 'mixed'")
        exit(1)

    # 2. Test Trend: Improving
    # Trend Logic checks first 1/3 vs last 1/3
    # Need at least 3 segments
    segments_improving = [
        # First 1/3 (Indices 0, 1 of 6 -> 0:2) -> Bad, Bad
        {"text": "Bad1", "start": 10.0, "end": 12.0, "sentiment": "Negative", "sentiment_confidence": 0.9},
        {"text": "Bad2", "start": 12.0, "end": 14.0, "sentiment": "Negative", "sentiment_confidence": 0.9},
        
        # Middle (Indices 2, 3) 
        {"text": "Ok", "start": 15.0, "end": 16.0, "sentiment": "Neutral", "sentiment_confidence": 0.9},
        {"text": "Ok", "start": 16.0, "end": 17.0, "sentiment": "Neutral", "sentiment_confidence": 0.9},
        
        # Last 1/3 (Indices -2:) -> Good, Good
        {"text": "Good1", "start": 20.0, "end": 22.0, "sentiment": "Positive", "sentiment_confidence": 0.9},
        {"text": "Good2", "start": 22.0, "end": 24.0, "sentiment": "Positive", "sentiment_confidence": 0.9},
    ]
    # Check length logic in function: n=6. n//3 = 2. first=[:2], last=[-2:]
    result_imp = analyze_sales(segments_improving)
    print(f"Trend Test Result: {result_imp['summary']['sentiment_trend']}")
    if result_imp["summary"]["sentiment_trend"] != "improving":
        print("FAIL: Expected 'improving'")
        exit(1)

    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_sales_logic()
