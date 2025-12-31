DECISION_KEYWORDS = [
    "we will",
    "let's",
    "agreed",
    "decided",
    "finalize",
    "moving forward"
]

ACTION_KEYWORDS = [
    "please",
    "can you",
    "need to",
    "will handle",
    "by",
    "before"
]

def aggregate_sentiment(segments):
    counts = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 0
    }

    for seg in segments:
        if seg["sentiment_confidence"] >= 0.6:
            counts[seg["sentiment"]] += 1

    return counts

def generate_meeting_summary(segments, sentiment_counts):
    total = sum(sentiment_counts.values())
    if total == 0:
        return "The meeting was largely informational."

    neg_ratio = sentiment_counts["Negative"] / total

    end_sentiment = segments[-1]["sentiment"]

    if neg_ratio > 0.3:
        return "The meeting involved several concerns and may require follow-up discussion."

    if sentiment_counts["Positive"] > sentiment_counts["Negative"] and end_sentiment == "Positive":
        return "The meeting was productive and concluded on a positive note."

    return "The meeting was primarily informational with neutral discussion."

def detect_decisions(segments):
    decisions = []

    for seg in segments:
        text = seg["text"].lower()
        if any(k in text for k in DECISION_KEYWORDS):
            if seg["sentiment_confidence"] >= 0.6:
                decisions.append({
                    "text": seg["text"],
                    "time": seg["start"]
                })

    return decisions

def extract_deadline(text):
    text = text.lower()
    for word in ["today", "tomorrow", "friday", "monday", "week"]:
        if word in text:
            return word.capitalize()
    return "Not specified"

def detect_action_items(segments):
    actions = []

    for seg in segments:
        text = seg["text"].lower()

        if any(k in text for k in ACTION_KEYWORDS):
            actions.append({
                "task": seg["text"],
                "owner": "Unassigned",
                "deadline": extract_deadline(seg["text"]),
                "time": seg["start"]
            })

    return actions

def detect_tension_points(segments):
    tension = []

    for seg in segments:
        if (
            seg["sentiment"] == "Negative"
            and seg["sentiment_confidence"] >= 0.75
        ):
            tension.append({
                "text": seg["text"],
                "time": seg["start"]
            })

    return tension

def analyze_meeting(enriched_segments: list) -> dict:
    """
    Main entry point for Meeting Mode analysis.
    Input: sentiment-enriched transcript segments
    Output: structured meeting intelligence
    """
    # 5.2 Normalize & Sort Transcript (Chronology First)
    segments = sorted(enriched_segments, key=lambda x: x["start"])

    # 5.3 Sentiment Aggregation (Core Signal)
    sentiment_counts = aggregate_sentiment(segments)

    # 5.4 Generate Meeting Summary (RULE-BASED)
    summary = generate_meeting_summary(segments, sentiment_counts)

    # 5.5 Detect Decisions Made
    decisions = detect_decisions(segments)

    # 5.6 Detect Action Items
    action_items = detect_action_items(segments)

    # 5.7 Detect Tension / Unresolved Moments
    tension_points = detect_tension_points(segments)

    # 5.8 Build Final Meeting Output
    return {
        "mode": "meeting",
        "summary": summary,
        "sentiment_overview": sentiment_counts,
        "decisions": decisions,
        "action_items": action_items,
        "tension_points": tension_points,
        "transcript": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "sentiment": seg["sentiment"],
                "confidence": seg["sentiment_confidence"]
            }
            for seg in segments
        ]
    }

def analyze_sales(nlp_input):
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
