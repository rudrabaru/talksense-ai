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

def analyze_sales(enriched_segments: list) -> dict:
    """
    Main entry point for Sales Mode analysis.
    """
    objections = []
    sentiment_dip = False
    follow_up_action = None
    
    # 1. Sort segments chronologically
    segments = sorted(enriched_segments, key=lambda x: x["start"])

    # Sales Keywords
    PRICE_WORDS = ["price", "cost", "expensive", "budget", "pricing", "discount"]
    FOLLOW_UP_WORDS = ["follow up", "next steps", "call again", "send details", "email me"]

    for seg in segments:
        text = seg["text"].lower()
        sentiment = seg["sentiment"] # "Positive", "Neutral", "Negative"
        confidence = seg["sentiment_confidence"]

        # 1️⃣ Objection detection (Simple keyword match for now)
        if any(w in text for w in PRICE_WORDS):
            if sentiment == "Negative":
                objections.append(f"Pricing objection: \"{seg['text']}\"")

        # 2️⃣ Sentiment dip detection (Strong negative sentiment)
        if sentiment == "Negative" and confidence >= 0.7:
            sentiment_dip = True

        # 3️⃣ Follow-up / next steps detection
        if any(w in text for w in FOLLOW_UP_WORDS):
            follow_up_action = seg["text"]

    # Remove duplicates
    objections = list(set(objections))

    # 4️⃣ Call score calculation
    score = 1.0
    if objections: score -= 0.3
    if sentiment_dip: score -= 0.2
    if not follow_up_action: score -= 0.1
    
    # Ensure score is healthy
    if any(seg["sentiment"] == "Positive" for seg in segments[-3:]):
        score += 0.1 # Bonus for positive closing

    score = max(0.0, min(score, 1.0))

    return {
        "mode": "sales",
        "objections": objections,
        "sentiment_dip": sentiment_dip,
        "call_score": round(score, 2),
        "follow_up": follow_up_action,
        "transcript": [
            {
                "start": seg["start"],
                "text": seg["text"],
                "sentiment": seg["sentiment"]
            }
            for seg in segments
        ]
    }
