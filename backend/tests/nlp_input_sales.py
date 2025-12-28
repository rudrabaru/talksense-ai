nlp_input_sales = {
  "segments": [
    {
      "speaker": "speaker_1",
      "text": "Okay, let’s start the meeting. Good morning everyone.",
      "sentiment": 0.3,
      "keywords": ["meeting_opening"]
    },
    {
      "speaker": "speaker_1",
      "text": "So the purpose of today’s call is to quickly discuss the product and see if it makes sense for your team.",
      "sentiment": 0.3,
      "keywords": ["meeting_purpose"]
    },
    {
      "speaker": "speaker_2",
      "text": "Can you explain what exactly this product does?",
      "sentiment": 0.1,
      "keywords": ["product_clarification", "client_question"]
    },
    {
      "speaker": "speaker_1",
      "text": "Yeah, so it’s basically a platform that helps manage workflows and reduce manual work.",
      "sentiment": 0.2,
      "keywords": ["product_explanation", "value_overview"]
    },
    {
      "speaker": "speaker_3",
      "text": "Is this something that can integrate with our existing systems?",
      "sentiment": 0.1,
      "keywords": ["integration_query", "technical_fit"]
    },
    {
      "speaker": "speaker_1",
      "text": "It should integrate with most systems, yes, although some setup might be required.",
      "sentiment": 0.1,
      "keywords": ["integration_capability", "setup_dependency"]
    },
    {
      "speaker": "speaker_4",
      "text": "I want to understand the pricing. It feels a bit expensive compared to alternatives.",
      "sentiment": -0.4,
      "keywords": ["price_objection"]
    },
    {
      "speaker": "speaker_1",
      "text": "Pricing is fixed, but many customers find value in the long run.",
      "sentiment": 0.2,
      "keywords": ["price_response", "value_justification"]
    },
    {
      "speaker": "speaker_5",
      "text": "What kind of support do you provide once we buy it?",
      "sentiment": 0.0,
      "keywords": ["support_query"]
    },
    {
      "speaker": "speaker_1",
      "text": "Support is mainly through tickets, and onboarding is provided initially.",
      "sentiment": 0.1,
      "keywords": ["support_model", "onboarding"]
    },
    {
      "speaker": "speaker_3",
      "text": "How long does implementation usually take?",
      "sentiment": 0.1,
      "keywords": ["implementation_timeline"]
    },
    {
      "speaker": "speaker_1",
      "text": "Usually a few days, depending on complexity.",
      "sentiment": 0.2,
      "keywords": ["timeline_estimate", "dependency"]
    },
    {
      "speaker": "speaker_2",
      "text": "Alright, what would be the next steps from here?",
      "sentiment": 0.0,
      "keywords": ["next_steps_query"]
    },
    {
      "speaker": "speaker_1",
      "text": "I’ll share the proposal and pricing details, and then you can review and get back to us.",
      "sentiment": 0.4,
      "keywords": ["follow_up", "next_steps"]
    },
    {
      "speaker": "speaker_1",
      "text": "Thanks everyone for joining.",
      "sentiment": 0.3,
      "keywords": ["meeting_closure"]
    }
  ]
}



# Practical sentiment scale (what you should use)
# Situation	Sentiment
# Purpose / agenda	+0.2 → +0.4
# Client questions	0.0 → +0.2
# Objections (price, trust)	-0.3 → -0.6
# Objection handling	+0.2 → +0.4
# Trust & support	+0.4 → +0.6
# Closing / next steps	+0.4 → +0.6
def analyze_sales(nlp_input_sales):
    objections = []
    sentiment_dip = False
    follow_up_action = None

    # Iterate over conversation segments
    for segment in nlp_input.get("segments", []):
        keywords = segment.get("keywords", [])
        sentiment = segment.get("sentiment", 0.0)
        text = segment.get("text", "")

        # 1️⃣ Objection detection
        if "price_objection" in keywords:
            objections.append("pricing")

        # 2️⃣ Sentiment dip detection
        if sentiment <= -0.3:
            sentiment_dip = True

        # 3️⃣ Follow-up / next steps detection
        if "follow_up" in keywords or "next_steps" in keywords:
            follow_up_action = text

    # Remove duplicate objections
    objections = list(set(objections))

    # 4️⃣ Call score calculation (simple & explainable)
    score = 1.0

    if objections:
        score -= 0.2

    if sentiment_dip:
        score -= 0.2

    if follow_up_action:
        score += 0.2

    # Clamp score between 0 and 1
    score = max(0.0, min(score, 1.0))

    return {
        "objections": objections,
        "sentiment_dip": sentiment_dip,
        "call_score": round(score, 2),
        "follow_up": follow_up_action
    }