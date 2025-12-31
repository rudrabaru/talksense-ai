import sys
import os

# Add backend directory to path so we can import services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.context_analyzer import analyze_meeting

def test_analyze_meeting():
    print("Testing Meeting Mode Context Analyzer...")

    # Mock Data (Unsorted to test sorting)
    enriched_segments = [
        {
            "start": 10.0,
            "end": 15.0,
            "text": "We need to finish the report by Friday.",
            "sentiment": "Neutral",
            "sentiment_confidence": 0.8
        },
        {
            "start": 0.0,
            "end": 5.0,
            "text": "Hello everyone, let's start properly.",
            "sentiment": "Positive",
            "sentiment_confidence": 0.9
        },
        {
            "start": 20.0,
            "end": 25.0,
            "text": "I am very worried about the timeline. This is bad.",
            "sentiment": "Negative",
            "sentiment_confidence": 0.85
        },
        {
            "start": 30.0,
            "end": 35.0,
            "text": "Okay, we decided to extend the deadline.",
            "sentiment": "Positive",
            "sentiment_confidence": 0.7
        }
    ]

    result = analyze_meeting(enriched_segments)

    # Check 1: Sorting
    print("\n[Check 1] Sorting...")
    transcript = result["transcript"]
    if transcript[0]["text"] == "Hello everyone, let's start properly." and transcript[-1]["text"] == "Okay, we decided to extend the deadline.":
        print("✔ Segments sorted correctly.")
    else:
        print("❌ Segments NOT sorted.")
        print(f"First: {transcript[0]['text']}")
        print(f"Last: {transcript[-1]['text']}")

    # Check 2: Action Items
    print("\n[Check 2] Action Items...")
    actions = result["action_items"]
    # "need to finish the report by Friday" -> Action
    if len(actions) > 0 and "need to" in actions[0]["task"] and actions[0]["deadline"] == "Friday":
        print("✔ Action item detected correctly with deadline.")
    else:
        print("❌ Action item detection failed.")
        print(actions)

    # Check 3: Decisions
    print("\n[Check 3] Decisions...")
    decisions = result["decisions"]
    # "decided to extend the deadline" -> Decision
    if len(decisions) > 0 and "decided" in decisions[0]["text"]:
        print("✔ Decision detected correctly.")
    else:
        print("❌ Decision detection failed.")
        print(decisions)

    # Check 4: Tension
    print("\n[Check 4] Tension Points...")
    tension = result["tension_points"]
    # "worried about the timeline" -> Negative sentiment
    if len(tension) > 0 and "worried" in tension[0]["text"]:
        print("✔ Tension point detected correctly.")
    else:
        print("❌ Tension detection failed.")
        print(tension)

    # Check 5: Summary
    print("\n[Check 5] Summary...")
    print(f"Summary: {result['summary']}")
    if result["summary"]:
         print("✔ Summary generated.")
    else:
         print("❌ Summary missing.")

    print("\nTest Complete.")

if __name__ == "__main__":
    test_analyze_meeting()
