import os
import json
import random
import shutil

# Paths
BASE_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DIRS = {
    "meeting": os.path.join(BASE_DIR, "meetings"),
    "sales": os.path.join(BASE_DIR, "sales"),
    "interview": os.path.join(BASE_DIR, "interviews")
}

# Clean existing datasets
for d in DIRS.values():
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d, exist_ok=True)

# Templates for Meetings
# Includes: Multi-speaker, negations, false triggers, multiple actions
MEETING_TEMPLATES = [
    {
        "desc": "standard",
        "segments": [
            ("Speaker 1", "Let's review the sprint. We need to deploy the new auth service by Friday.", "Neutral"),
            ("Speaker 2", "I will deploy the auth service.", "Positive"),
            ("Speaker 1", "Great, let's lock the database schema changes.", "Positive")
        ],
        "expected_action_items": [{"task": "deploy the auth service by Friday", "owner": "Speaker 2", "deadline": "Friday"}],
        "expected_decisions": ["lock the database schema changes"],
        "expected_commitments": ["I will deploy the auth service"],
        "expected_sentiment": {"Positive": 2, "Neutral": 1, "Negative": 0}
    },
    {
        "desc": "explicit_negation_and_false_trigger",
        "segments": [
            ("Speaker 1", "Are we going to ship the beta today?", "Neutral"),
            ("Speaker 2", "I will not ship the beta today because of the bug.", "Negative"),
            ("Speaker 3", "Agreed. Let's not delay the bug fix any further.", "Neutral")
        ],
        "expected_action_items": [],
        "expected_decisions": ["not delay the bug fix"],
        "expected_commitments": [],
        "expected_sentiment": {"Positive": 0, "Neutral": 2, "Negative": 1}
    },
    {
        "desc": "long_meeting_multiple_actions",
        "segments": [
            ("Speaker 1", "First, I'll follow up with the design team.", "Neutral"),
            ("Speaker 2", "I can confirm the requirements with the client.", "Neutral"),
            ("Speaker 1", "Perfect. Let's go with the blue theme.", "Positive"),
            ("Speaker 3", "I will assign the tickets to the backend team.", "Neutral")
        ],
        "expected_action_items": [
            {"task": "follow up with the design team", "owner": "Speaker 1"},
            {"task": "confirm the requirements", "owner": "Speaker 2"},
            {"task": "assign the tickets", "owner": "Speaker 3"}
        ],
        "expected_decisions": ["go with the blue theme"],
        "expected_commitments": ["I'll follow up", "I can confirm", "I will assign"],
        "expected_sentiment": {"Positive": 1, "Neutral": 3, "Negative": 0}
    },
    {
        "desc": "interruptions_and_contradictions",
        "segments": [
            ("Speaker 1", "I'll handle the API...", "Neutral"),
            ("Speaker 2", "Wait, no, I am going to handle the API integration.", "Neutral"),
            ("Speaker 1", "Okay, then we decided to let you handle it.", "Positive")
        ],
        "expected_action_items": [{"task": "handle the API integration", "owner": "Speaker 2"}],
        "expected_decisions": ["decided to let you handle it"],
        "expected_commitments": ["I am going to handle"],
        "expected_sentiment": {"Positive": 1, "Neutral": 2, "Negative": 0}
    }
]

# Templates for Sales
# Includes: Hidden objections, soft/strong buying signals, conditionals, authority
SALES_TEMPLATES = [
    {
        "desc": "soft_buying_signal_and_budget",
        "segments": [
            ("Speaker 1", "Our solution integrates smoothly with your stack.", "Positive"),
            ("Speaker 2", "Makes sense. And it fits the budget.", "Positive"),
            ("Speaker 1", "Awesome. I will send the proposal by Monday.", "Neutral")
        ],
        "expected_objections": [],
        "expected_buying_signals": ["makes sense", "fits the budget"],
        "expected_commitments": ["will send the proposal"],
        "expected_sentiment": {"Positive": 2, "Neutral": 1, "Negative": 0}
    },
    {
        "desc": "hidden_objection_and_conditional",
        "segments": [
            ("Speaker 1", "How do you feel about the platform?", "Neutral"),
            ("Speaker 2", "It looks good, but I'm not the decision maker. I need to run it by colleagues.", "Neutral"),
            ("Speaker 2", "Also, it seems a bit expensive right now.", "Negative")
        ],
        "expected_objections": ["not the decision maker", "expensive", "run it by colleagues"],
        "expected_buying_signals": [],
        "expected_commitments": [],
        "expected_sentiment": {"Positive": 0, "Neutral": 2, "Negative": 1}
    },
    {
        "desc": "no_intent_and_deferral",
        "segments": [
            ("Speaker 1", "Are you looking to migrate soon?", "Neutral"),
            ("Speaker 2", "Honestly, we are just exploring. Not planning to switch this quarter.", "Negative"),
            ("Speaker 1", "Understood. Should I circle back later this year?", "Neutral"),
            ("Speaker 2", "Yes please do that.", "Positive")
        ],
        "expected_objections": ["just exploring", "not planning to switch", "later this year"],
        "expected_buying_signals": [],
        "expected_commitments": ["circle back", "yes please do that"],
        "expected_sentiment": {"Positive": 1, "Neutral": 2, "Negative": 1}
    },
    {
        "desc": "false_trigger_phrase",
        "segments": [
            ("Speaker 2", "I would be interested if it had more features, but right now it doesn't solve our problem.", "Negative"),
            ("Speaker 1", "We will release new features next month.", "Positive")
        ],
        "expected_objections": ["doesn't solve our problem"],
        "expected_buying_signals": [],
        "expected_commitments": ["We will release"],
        "expected_sentiment": {"Positive": 1, "Neutral": 0, "Negative": 1}
    }
]

# Templates for Interviews
INTERVIEW_TEMPLATES = [
    {
        "desc": "behavioral",
        "segments": [
            ("Interviewer", "Tell me about a time you had a conflict.", "Neutral"),
            ("Candidate", "I once had a disagreement over a system architecture.", "Neutral"),
            ("Candidate", "We decided to write a design doc, which resolved it.", "Positive")
        ],
        "expected_action_items": [],
        "expected_decisions": ["decided to write a design doc"],
        "expected_commitments": [],
        "expected_sentiment": {"Positive": 1, "Neutral": 2, "Negative": 0}
    },
    {
        "desc": "technical_weak",
        "segments": [
            ("Interviewer", "How do you optimize a React app?", "Neutral"),
            ("Candidate", "Um, I am not really sure. Maybe use memo?", "Negative")
        ],
        "expected_action_items": [],
        "expected_decisions": [],
        "expected_commitments": [],
        "expected_sentiment": {"Positive": 0, "Neutral": 1, "Negative": 1}
    }
]

def generate_file(idx, template, mode, output_dir):
    data = {
        "id": f"{mode}_{idx:02d}",
        "mode": mode,
        "segments": [],
        "expected_action_items": template.get("expected_action_items", []),
        "expected_decisions": template.get("expected_decisions", []),
        "expected_commitments": template.get("expected_commitments", []),
        "expected_objections": template.get("expected_objections", []),
        "expected_buying_signals": template.get("expected_buying_signals", []),
        "expected_sentiment": template.get("expected_sentiment", {}),
        "expected_alerts": []
    }
    
    current_time = 0.0
    for speaker, text, sentiment in template["segments"]:
        data["segments"].append({
            "start": current_time,
            "end": current_time + 3.0,
            "speaker": speaker,
            "text": text,
            "sentiment_label": sentiment,
            "sentiment_confidence": 0.95
        })
        current_time += 3.0
        
    with open(os.path.join(output_dir, f"{data['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

print("Generating Datasets...")
# Generate 20 Meetings
for i in range(1, 21):
    t = random.choice(MEETING_TEMPLATES)
    generate_file(i, t, "meeting", DIRS["meeting"])

# Generate 20 Sales
for i in range(1, 21):
    t = random.choice(SALES_TEMPLATES)
    generate_file(i, t, "sales", DIRS["sales"])

# Generate 10 Interviews
for i in range(1, 11):
    t = random.choice(INTERVIEW_TEMPLATES)
    generate_file(i, t, "interview", DIRS["interview"])
    
print("Successfully generated 50 dataset files.")
