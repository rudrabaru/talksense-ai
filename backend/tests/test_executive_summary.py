import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.context_analyzer import (
    extract_primary_topic,
    assess_decision_state,
    assess_action_clarity,
    assess_risk_level,
    compose_executive_summary
)

def test_signal_extraction_hardened():
    print("Testing Hardened Signal Extraction...")
    
    # 1. Topic Extraction: Robustness against noise
    segments_noise = [
        {"text": "Yeah, so basically..."},
        {"text": "Right, okay, maybe."},
        {"text": "We discussed the onboarding flow."} # Matches 'onboarding' bucket
    ]
    topic = extract_primary_topic(segments_noise)
    print(f"Topic (noise + 'onboarding'): {topic}")
    assert topic == "onboarding"

    segments_pure_noise = [
        {"text": "Yeah, cool."},
        {"text": "Whatever you say."}
    ]
    topic_fallback = extract_primary_topic(segments_pure_noise)
    print(f"Topic (pure noise -> expected 'general discussion'): {topic_fallback}")
    assert topic_fallback == "general discussion"

    # 2. Action Clarity: Strong vs Weak
    actions_weak = [{"task": "We should maybe look into this."}]
    clarity_weak = assess_action_clarity(actions_weak)
    print(f"Action Clarity (weak -> expected 'no clear next steps'): {clarity_weak}")
    assert clarity_weak == "no clear next steps"

    actions_strong = [{"task": "I will assign this to the team."}]
    clarity_strong = assess_action_clarity(actions_strong)
    print(f"Action Clarity (strong -> expected 'next steps identified'): {clarity_strong}")
    assert clarity_strong == "next steps identified"

    print("Hardened Signal Extraction Tests Passed!\n")

def test_summary_composition_hardened():
    print("Testing Hardened Summary Composition...")
    
    # 1. Guardrail: Generic Topic
    signals_generic = {
        "topic": "general discussion",
        "decision_state": "no final decision",
        "action_clarity": "no clear next steps",
        "risk": "low"
    }
    summary_generic = compose_executive_summary(signals_generic)
    print(f"Summary (Generic Topic -> 'key issues'):\n{summary_generic}\n")
    assert "key issues" in summary_generic

    # 2. Risk Logic: Indecision + No Actions + Risk
    signals_risky = {
        "topic": "performance",
        "decision_state": "no final decision",
        "action_clarity": "no clear next steps",
        "risk": "elevated"
    }
    summary_risky = compose_executive_summary(signals_risky)
    print(f"Summary (Risky Stagnation):\n{summary_risky}\n")
    assert "lack of clear next steps poses a risk" in summary_risky

    print("Hardened Summary Composition Tests Passed!")

if __name__ == "__main__":
    test_signal_extraction_hardened()
    test_summary_composition_hardened()
