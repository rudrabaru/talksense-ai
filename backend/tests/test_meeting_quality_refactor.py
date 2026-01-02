"""
STEP 10: Regression Test for Meeting Quality Refactor

This test ensures that meetings with:
- Blockers mentioned
- Concerns expressed  
- Explicit ownership ("I'll follow up")
- Explicit decisions ("Decision is...")

Result in:
- meeting_quality: "High" (because ownership + decision exist)
- project_risk: "Medium" or "High" (because blockers exist)

This validates that sentiment and issues DO NOT lower meeting quality.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.context_analyzer import analyze_meeting

def test_blockers_with_ownership_and_decision():
    """
    CRITICAL TEST: Meeting with blockers + ownership + decision should be High quality.
    """
    # Simulated enriched segments with:
    # 1. Blocker mentioned
    # 2. Concern expressed
    # 3. Ownership commitment
    # 4. Decision made
    test_segments = [
        {
            "start": 0.0,
            "end": 5.0,
            "text": "We're blocked on the API approval from the security team.",
            "sentiment": -0.5,
            "sentiment_label": "Negative",
            "sentiment_confidence": 0.8,
            "keywords": ["blocker"]
        },
        {
            "start": 5.0,
            "end": 10.0,
            "text": "There's a concern about the timeline impact on our release.",
            "sentiment": -0.3,
            "sentiment_label": "Negative",
            "sentiment_confidence": 0.7,
            "keywords": ["timeline_risk"]
        },
        {
            "start": 10.0,
            "end": 15.0,
            "text": "I'll follow up with the security team tomorrow to get approval.",
            "sentiment": 0.0,
            "sentiment_label": "Neutral",
            "sentiment_confidence": 0.6,
            "keywords": ["action_item"]
        },
        {
            "start": 15.0,
            "end": 20.0,
            "text": "Decision is to proceed with the current approach once we get approval.",
            "sentiment": 0.2,
            "sentiment_label": "Positive",
            "sentiment_confidence": 0.7,
            "keywords": ["decision_made"]
        },
        {
            "start": 20.0,
            "end": 25.0,
            "text": "We'll review the timeline on Friday to see if we need to adjust.",
            "sentiment": 0.0,
            "sentiment_label": "Neutral",
            "sentiment_confidence": 0.6,
            "keywords": []
        }
    ]
    
    nlp_input = {"segments": test_segments}
    
    result = analyze_meeting(nlp_input)
    
    # ASSERTIONS
    print("\n=== REGRESSION TEST RESULTS ===")
    print(f"Meeting Quality: {result['meeting_quality']}")
    print(f"Project Risk: {result['project_risk']}")
    print(f"Summary: {result['summary']}")
    
    # CRITICAL: Meeting quality MUST be High
    assert result["meeting_quality"]["label"] == "High", \
        f"FAILED: Expected meeting_quality='High', got '{result['meeting_quality']['label']}'"
    
    # Project risk should be Medium or High (due to blockers)
    assert result["project_risk"]["label"] in ["Medium", "High"], \
        f"FAILED: Expected project_risk='Medium' or 'High', got '{result['project_risk']['label']}'"
    
    # Summary should NOT say "no ownership" or "no decisions"
    summary_lower = result["summary"].lower()
    assert "no ownership" not in summary_lower, \
        "FAILED: Summary says 'no ownership' when ownership exists"
    assert "no decision" not in summary_lower, \
        "FAILED: Summary says 'no decision' when decision exists"
    
    # Summary SHOULD mention ownership and decisions positively
    assert any(word in summary_lower for word in ["ownership", "next steps", "decision"]), \
        "FAILED: Summary doesn't mention ownership or decisions"
    
    print("\n✅ ALL TESTS PASSED!")
    print("Meeting quality is correctly HIGH despite blockers and negative sentiment.")
    print("Project risk is correctly elevated due to blockers.")
    print("Summary correctly emphasizes ownership and decisions without contradiction.")
    
    return result

if __name__ == "__main__":
    test_blockers_with_ownership_and_decision()
