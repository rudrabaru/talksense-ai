import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.context_analyzer import evaluate_meeting_health, generate_key_insights

def test_meeting_health_scenarios():
    print("Testing Meeting Health Logic...\n")

    # Scenario 1: Decisive Meeting
    # Conditions: Decisions Made, Actions Assigned, No Blockers. Sentiment is Negative (complaining about bugs).
    # Expect: Good (Outcome Override)
    decisions_1 = [{"text": "We will ship."}]
    actions_1 = [{"task": "Fix bug", "owner": "John"}] # Assigned
    blockers_1 = []
    # Negative sentiment - would normally trigger Uncertain or At Risk
    sentiment_1 = {"Positive": 0, "Negative": 10, "Neutral": 0} 
    segments_1 = [] # Irrelevant for override

    health_1 = evaluate_meeting_health(decisions_1, actions_1, blockers_1, sentiment_1, segments_1)
    print(f"Scenario 1 (Decisive, High Negativity): {health_1}")
    assert health_1 == "good"

    # Verify Key Insights suppression for Good outcome (e.g. Execution Risk should not trigger even if actions are weird, though usually assigned actions implies strong)
    # Let's say we have Good outcome.
    signals_1 = {
        "topic": "bugs", 
        "decision_state": "decision made", 
        "action_clarity": "next steps identified",
        "risk": "moderate" # Artificial risk signal
    }
    insights_1 = generate_key_insights(signals_1, actions_1, decisions_1, blockers_1, health_1)
    print(f"Scenario 1 Insights: {[i['type'] for i in insights_1]}")
    # Should result in Positive Momentum
    assert "Positive Momentum" in [i["type"] for i in insights_1]


    # Scenario 2: Vague Meeting
    # Conditions: No Decisions, No Actions. Positive Sentiment ("Great chat!").
    # Expect: Neutral (or Uncertain if sentiment was super negative, but here Positive -> Neutral)
    decisions_2 = []
    actions_2 = []
    blockers_2 = []
    sentiment_2 = {"Positive": 10, "Negative": 0, "Neutral": 0}
    
    health_2 = evaluate_meeting_health(decisions_2, actions_2, blockers_2, sentiment_2, [])
    print(f"Scenario 2 (Vague, Positive): {health_2}")
    # Code logic: Override=False, Blockers=False. NegRatio=0. -> return "neutral".
    assert health_2 == "neutral"


    # Scenario 3: Blocked Meeting (Explicit Blocker, No Override)
    # Expect: At Risk
    blockers_3 = [{"text": "We are stuck."}]
    health_3 = evaluate_meeting_health([], [], blockers_3, {}, [])
    print(f"Scenario 3 (Blocked): {health_3}")
    assert health_3 == "at_risk"

    # Scenario 3B: Blocked BUT Explicitly Overridden
    # "Any blockers? None." -> Should clear the blocker list internally and return Good
    segments_3b = [{"text": "Any blockers? None from my side."}]
    health_3b = evaluate_meeting_health([], [], blockers_3, {}, segments_3b)
    print(f"Scenario 3B (Blocked + Override): {health_3b}")
    assert health_3b == "good"

    # Scenario 5: Dependencies (Controlled vs Uncontrolled)
    # A: Controlled (Owner + Time) -> Good
    actions_5a = [{"task": "Get QA approval by tomorrow", "owner": "Bob", "timeline": "tomorrow"}]
    # Note: Logic checks 'task' text for timestamp if 'timeline' key missing, or the key. 
    # My helpers look for TEMPORAL_KEYWORDS in task.
    health_5a = evaluate_meeting_health([], actions_5a, [], {}, [])
    print(f"Scenario 5A (Controlled Dependency): {health_5a}")
    assert health_5a == "good"

    # B: Uncontrolled (Unassigned) -> At Risk
    actions_5b = [{"task": "Need explicit approval from legal", "owner": "Unassigned"}]
    health_5b = evaluate_meeting_health([], actions_5b, [], {}, [])
    print(f"Scenario 5B (Uncontrolled Dependency): {health_5b}")
    assert health_5b == "at_risk"

    print("\nMeeting Health Tests Passed!")

if __name__ == "__main__":
    test_meeting_health_scenarios()
