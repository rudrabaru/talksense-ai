
import sys
import os
import unittest

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

from services.context_analyzer import (
    analyze_sales,
    overall_call_sentiment,
    sentiment_trend,
    detect_objections,
    detect_buying_signals,
    engagement_level,
    recommend_actions,
    key_moments
)

class TestSalesMode(unittest.TestCase):

    def setUp(self):
        # Sample segments based on requirements
        self.segments_mixed = [
            {"text": "Hello", "start": 0.0, "end": 1.0, "sentiment": "Neutral", "sentiment_confidence": 0.9},
            {"text": "The price is too high", "start": 2.0, "end": 3.0, "sentiment": "Negative", "sentiment_confidence": 0.8}, # Objection
            {"text": "I like this feature", "start": 4.0, "end": 5.0, "sentiment": "Positive", "sentiment_confidence": 0.5}, # Low conf ignored
            {"text": "It sounds good", "start": 6.0, "end": 7.0, "sentiment": "Positive", "sentiment_confidence": 0.8}, # Buying Signal
            {"text": "We need approval", "start": 8.0, "end": 9.0, "sentiment": "Negative", "sentiment_confidence": 0.9}, # Objection (Authority)
            {"text": "Okay bye", "start": 10.0, "end": 11.0, "sentiment": "Neutral", "sentiment_confidence": 0.9}
        ]

    def test_overall_call_sentiment(self):
        # 1 Pos (conf>0.6), 2 Neg (conf>0.6) -> Negative > Positive -> "negative"??
        # Counts: Neg=2 ("price", "approval"), Pos=1 ("sounds good")
        # Neg > Pos -> "negative"
        self.assertEqual(overall_call_sentiment(self.segments_mixed), "negative")
        
        # Test positive case
        pos_segs = [
            {"text": "Great", "sentiment": "Positive", "sentiment_confidence": 0.9},
            {"text": "Good", "sentiment": "Positive", "sentiment_confidence": 0.9}
        ]
        self.assertEqual(overall_call_sentiment(pos_segs), "positive")

    def test_sentiment_trend(self):
        # Segments length = 6. n//3 = 2.
        # First: Neutral (0), Negative (-1) -> Score -1
        # Last: Negative (-1), Neutral (0) -> Score -1
        # Trend: Flat
        self.assertEqual(sentiment_trend(self.segments_mixed), "flat")

        # Test Improving
        # First: Neg, Neg -> -2
        # Last: Pos, Pos -> +2
        improving_segs = [
            {"sentiment": "Negative", "sentiment_confidence": 0.8},
            {"sentiment": "Negative", "sentiment_confidence": 0.8},
            {"sentiment": "Neutral", "sentiment_confidence": 0.8},
            {"sentiment": "Neutral", "sentiment_confidence": 0.8},
            {"sentiment": "Positive", "sentiment_confidence": 0.8},
            {"sentiment": "Positive", "sentiment_confidence": 0.8}
        ]
        self.assertEqual(sentiment_trend(improving_segs), "improving")

    def test_detect_objections(self):
        objections = detect_objections(self.segments_mixed)
        # Should detect "price" and "approval"
        self.assertEqual(len(objections), 2)
        types = [o["type"] for o in objections]
        self.assertIn("Pricing", types)
        self.assertIn("Authority", types)

        # Test confidence threshold (ignore if < 0.75)
        low_conf_obj = [{"text": "price is bad", "start": 1, "sentiment": "Negative", "sentiment_confidence": 0.7}]
        self.assertEqual(len(detect_objections(low_conf_obj)), 0)

    def test_detect_buying_signals(self):
        signals = detect_buying_signals(self.segments_mixed)
        # Should detect "sounds good"
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["text"], "It sounds good")

        # Test confidence threshold (< 0.7)
        low_conf_sig = [{"text": "sounds good", "start": 1, "sentiment": "Positive", "sentiment_confidence": 0.6}]
        self.assertEqual(len(detect_buying_signals(low_conf_sig)), 0)

    def test_engagement_level(self):
        # Mixed has Pos and Neg -> High
        self.assertEqual(engagement_level(self.segments_mixed), "high")

    def test_recommend_actions(self):
        objections = [
            {"type": "Pricing"},
            {"type": "Authority"}
        ]
        buying_signals = [{"text": "buy"}]
        trend = "flat"
        
        actions = recommend_actions(objections, buying_signals, trend)
        self.assertIn("Send pricing clarification", actions)
        self.assertIn("Follow up after internal discussion", actions)
        self.assertIn("Send proposal", actions)
        self.assertIn("Schedule follow-up call", actions)

    def test_analyze_sales_structure(self):
        result = analyze_sales(self.segments_mixed)
        self.assertEqual(result["mode"], "sales")
        self.assertIn("summary", result)
        self.assertIn("objections", result)
        self.assertIn("buying_signals", result)
        self.assertIn("recommended_actions", result)
        self.assertIn("key_moments", result)
        self.assertIn("transcript", result)

if __name__ == '__main__':
    unittest.main()
