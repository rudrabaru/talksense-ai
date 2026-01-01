import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.context_analyzer import generate_key_insights

def test_refined_key_insights():
    print("Testing Refined Key Insights Logic...\n")

    # 1. Test Collapse Logic (Risk > Ambiguity)
    # Scenario: No decision + Weak actions
    # Ambiguity (no decision) matches.
    # Risk (weak actions) matches.
    # Expect: Execution Risk ONLY (Ambiguity removed)
    signals_overlap = {
        "topic": "refactoring",
        "decision_state": "no final decision",
        "action_clarity": "no clear next steps",
        "risk": "low"
    }
    actions_weak = [{"task": "We should refactor.", "owner": "Unassigned"}]
    
    insights = generate_key_insights(signals_overlap, actions_weak, [], [])
    print(f"Scenario 1 (Collapse): { [i['type'] for i in insights] }")
    types = [i["type"] for i in insights]
    assert "Execution Risk" in types
    assert "Decision Ambiguity" not in types

    # 2. Test Escalation Guardrail
    # Scenario: High Risk but NO tension points
    # Expect: NO Escalation Required insight
    signals_risk_high = {
        "topic": "outage",
        "decision_state": "no final decision",
        "action_clarity": "no clear next steps",
        "risk": "elevated"
    }
    insights_guardrail = generate_key_insights(signals_risk_high, [], [], []) # Empty tension
    print(f"Scenario 2 (Escalation Guardrail): { [i['type'] for i in insights_guardrail] }")
    assert "Escalation Required" not in [i["type"] for i in insights_guardrail]

    # Scenario: High Risk + Tension
    # Expect: Escalation Required
    insights_escalate = generate_key_insights(signals_risk_high, [], [], [{"text": "Blocked"}])
    print(f"Scenario 3 (Escalation Trigger): { [i['type'] for i in insights_escalate] }")
    assert "Escalation Required" in [i["type"] for i in insights_escalate]
    
    # 3. Test Capping (Max 2)
    # Scenario: Trigger Risk, Ambiguity, Gap (Unlikely due to collapse, but let's try to force 3)
    # Risk, Gap, and ... maybe Positive? No, Positive needs decision.
    # Let's try: Risk (weak actions), Gap (all unassigned - wait, Gap requires actions. If Risk (weak actions) usually implies Gap too if unassigned).
    # If we have weak actions + unassigned:
    # - Risk triggers.
    # - Gap triggers (actions exist, unassigned).
    # - Ambiguity triggers (no decision).
    # Collapse removes Ambiguity if Risk is present.
    # So we get Risk + Gap. That's 2.
    # If we add Escalation:
    # Escalation + Risk + Gap.
    # Sorted: Escalation, Risk, Gap.
    # Cap: Escalation, Risk.
    
    signals_max = {
        "topic": "chaos",
        "decision_state": "no final decision",
        "action_clarity": "no clear next steps",
        "risk": "elevated"
    }
    actions_chaos = [{"task": "maybe fix", "owner": "Unassigned"}] # triggers Risk and Gap
    tension_chaos = [{"text": "Fire"}] # triggers Escalation
    
    insights_capped = generate_key_insights(signals_max, actions_chaos, [], tension_chaos)
    print(f"Scenario 4 (Capping): { [i['type'] for i in insights_capped] }")
    assert len(insights_capped) <= 2
    assert "Escalation Required" in [i["type"] for i in insights_capped] # Priority 0
    assert "Execution Risk" in [i["type"] for i in insights_capped]      # Priority 1
    assert "Ownership Gap" not in [i["type"] for i in insights_capped]   # Priority 3 (Dropped)

    print("\nRefined Tests Passed!")

if __name__ == "__main__":
    test_refined_key_insights()
