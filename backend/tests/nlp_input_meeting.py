nlp_input_meeting = {
  "segments": [
    {
      "speaker": "manager",
      "text": "Good morning everyone. Let’s get started. The objective of today’s meeting is to review progress on the current sprint and decide next steps.",
      "sentiment": 0.4,
      "keywords": ["meeting_opening", "meeting_objective", "decision_focus"]
    },
    {
      "speaker": "team_lead",
      "text": "Overall progress is on track, but we have a few dependencies that need attention.",
      "sentiment": 0.2,
      "keywords": ["status_update", "dependencies"]
    },
    {
      "speaker": "developer_1",
      "text": "From the backend side, most features are complete. However, we’re blocked on the database migration approval.",
      "sentiment": -0.2,
      "keywords": ["backend_status", "blocker", "migration_approval"]
    },
    {
      "speaker": "manager",
      "text": "What’s causing the delay there?",
      "sentiment": 0.1,
      "keywords": ["clarification_request"]
    },
    {
      "speaker": "developer_1",
      "text": "The schema changes are ready, but we’re waiting for final sign-off from the infrastructure team.",
      "sentiment": -0.2,
      "keywords": ["external_dependency", "approval_pending"]
    },
    {
      "speaker": "developer_2",
      "text": "On the frontend, integration testing hasn’t started yet because the updated APIs aren’t deployed.",
      "sentiment": -0.3,
      "keywords": ["frontend_blocked", "api_dependency"]
    },
    {
      "speaker": "manager",
      "text": "Understood. So both teams are blocked due to the same dependency.",
      "sentiment": 0.1,
      "keywords": ["dependency_identified", "alignment"]
    },
    {
      "speaker": "product_manager",
      "text": "I’m a bit concerned because this could impact the delivery timeline for the release.",
      "sentiment": -0.4,
      "keywords": ["timeline_risk", "concern"]
    },
    {
      "speaker": "team_lead",
      "text": "If we get approval today, we should be able to deploy and catch up by the end of the week.",
      "sentiment": 0.3,
      "keywords": ["mitigation_plan", "recovery_timeline"]
    },
    {
      "speaker": "manager",
      "text": "Alright. I’ll follow up with the infrastructure team immediately after this meeting.",
      "sentiment": 0.5,
      "keywords": ["action_item", "ownership"]
    },
    {
      "speaker": "manager",
      "text": "Once deployment is done, frontend can start integration testing by tomorrow, correct?",
      "sentiment": 0.2,
      "keywords": ["dependency_resolution", "confirmation"]
    },
    {
      "speaker": "developer_2",
      "text": "Yes, that should work.",
      "sentiment": 0.2,
      "keywords": ["confirmation"]
    },
    {
      "speaker": "manager",
      "text": "Okay, decision is to prioritize the database approval today and review progress in tomorrow’s sync.",
      "sentiment": 0.6,
      "keywords": ["decision_made", "priority_set"]
    },
    {
      "speaker": "manager",
      "text": "I’ll send out the action items and updated timeline shortly. Thanks everyone, let’s wrap up.",
      "sentiment": 0.4,
      "keywords": ["action_items", "meeting_closure"]
    }
  ]
}

# 🔹 Sentiment Scale Used

# I implicitly used a −1.0 to +1.0 scale:

# Range	Meaning
# +0.7 to +1.0	Strong confidence / decision
# +0.3 to +0.6	Constructive / forward-moving
# −0.1 to +0.1	Neutral / informational
# −0.3 to −0.6	Risk, delay, vagueness
# −0.7 to −1.0	Avoidance, confusion, derailment