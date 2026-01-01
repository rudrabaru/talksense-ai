import sys
import os

# Ensure we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import KEYWORDS_CONFIG

# Load Configured Keywords (or defaults)
DECISION_KEYWORDS = KEYWORDS_CONFIG["meeting"]["decisions"]
ACTION_KEYWORDS = KEYWORDS_CONFIG["meeting"]["actions"]

# --- SALES MODE HELPERS ---
OBJECTION_KEYWORDS = KEYWORDS_CONFIG["sales"]["objections"]
BUYING_KEYWORDS = KEYWORDS_CONFIG["sales"]["buying_signals"]

def aggregate_sentiment(segments):
    counts = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 0
    }

    for seg in segments:
        # Use sentiment_label (String)
        label = seg.get("sentiment_label", "Neutral")
        if label in counts:
            counts[label] += 1

    return counts

def generate_meeting_summary(segments, sentiment_counts):
    total = sum(sentiment_counts.values())
    if total == 0:
        return "The meeting was largely informational."

    neg_ratio = sentiment_counts["Negative"] / total

    # Use sentiment_label (String)
    end_sentiment = segments[-1].get("sentiment_label", "Neutral")

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
            # Lower confidence threshold slightly as model scores might vary
            if seg.get("sentiment_confidence", 0) >= 0.5:
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
        # Use sentiment_label (String)
        if (
            seg.get("sentiment_label") == "Negative"
            and seg.get("sentiment_confidence", 0) >= 0.75
        ):
            tension.append({
                "text": seg["text"],
                "time": seg["start"]
            })

    return tension

def analyze_meeting(nlp_input: dict) -> dict:
    """
    Main entry point for Meeting Mode analysis.
    Input: sentiment-enriched transcript dictionary
    Output: structured meeting intelligence
    """
    # Extract segments list from input dict
    enriched_segments = nlp_input.get("segments", [])

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
                "sentiment": seg["sentiment"], # Keep float for frontend
                "confidence": seg.get("sentiment_confidence", 0)
            }
            for seg in segments
        ]
    }


# --- SALES MODE HELPERS ---

OBJECTION_KEYWORDS = {
    "Pricing": ["price", "cost", "expensive", "budget"],
    "Timeline": ["delay", "later", "timeline", "next quarter"],
    "Authority": ["approval", "discuss internally", "check with"],
    "Fit": ["not suitable", "concern", "issue"],
    "Competition": ["already using", "other vendor"]
}

BUYING_KEYWORDS = [
    "sounds good",
    "makes sense",
    "next steps",
    "how do we proceed",
    "what's next",
    "within budget",
    "interested"
]

def overall_call_sentiment(segments):
    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    for seg in segments:
        if seg["sentiment_confidence"] >= 0.6:
            # Use sentiment_label for string keys (Positive/Negative/Neutral)
            label = seg.get("sentiment_label", "Neutral")
            if label in counts:
                counts[label] += 1

    if counts["Negative"] > counts["Positive"]:
        return "negative"
    if counts["Positive"] > counts["Negative"]:
        return "positive"
    if counts["Positive"] > 0 and counts["Negative"] > 0:
        return "mixed"
    return "neutral"

def sentiment_trend(segments):
    n = len(segments)
    if n < 3:
        return "insufficient data"

    first = segments[: n // 3]
    last = segments[-(n // 3):]

    def score(segs):
        return sum(
            1 if s.get("sentiment_label") == "Positive"
            else -1 if s.get("sentiment_label") == "Negative"
            else 0
            for s in segs
            if s["sentiment_confidence"] >= 0.6
        )

    start_score = score(first)
    end_score = score(last)

    if end_score > start_score:
        return "improving"
    if end_score < start_score:
        return "declining"
    return "flat"

def detect_objections(segments):
    objections = []

    for seg in segments:
        label = seg.get("sentiment_label", "Neutral")
        if label != "Negative" or seg["sentiment_confidence"] < 0.75:
            continue

        text = seg["text"].lower()

        for obj_type, keywords in OBJECTION_KEYWORDS.items():
            if any(k in text for k in keywords):
                objections.append({
                    "type": obj_type,
                    "text": seg["text"],
                    "time": seg["start"]
                })

    return objections

def detect_buying_signals(segments):
    signals = []

    for seg in segments:
        label = seg.get("sentiment_label", "Neutral")
        if label != "Positive" or seg["sentiment_confidence"] < 0.7:
            continue

        text = seg["text"].lower()
        if any(k in text for k in BUYING_KEYWORDS):
            signals.append({
                "text": seg["text"],
                "time": seg["start"]
            })

    return signals

def engagement_level(segments):
    sentiments = [
        s.get("sentiment_label", "Neutral")
        for s in segments
        if s["sentiment_confidence"] >= 0.6
    ]

    if sentiments.count("Positive") + sentiments.count("Negative") == 0:
        return "low"
    if sentiments.count("Positive") > 0 and sentiments.count("Negative") > 0:
        return "high"
    return "medium"

def recommend_actions(objections, buying_signals, trend):
    actions = []

    if any(o["type"] == "Pricing" for o in objections):
        actions.append("Send pricing clarification")

    if any(o["type"] == "Authority" for o in objections):
        actions.append("Follow up after internal discussion")

    if buying_signals:
        actions.append("Send proposal")

    if trend == "flat":
        actions.append("Schedule follow-up call")

    return list(set(actions))

def key_moments(objections, buying_signals):
    events = []

    for o in objections:
        events.append({
            "time": o["time"],
            "event": f"{o['type']} objection detected"
        })

    for b in buying_signals:
        events.append({
            "time": b["time"],
            "event": "Buying signal detected"
        })

    return sorted(events, key=lambda x: x["time"])

def analyze_sales(enriched_segments: list) -> dict:
    """
    Main entry point for Sales Mode analysis.
    """
    if not enriched_segments:
        return {
            "mode": "sales",
            "summary": {},
            "objections": [],
            "buying_signals": [],
            "recommended_actions": [],
            "key_moments": [],
            "transcript": []
        }

    segments = sorted(enriched_segments, key=lambda x: x["start"])

    call_sentiment = overall_call_sentiment(segments)
    trend = sentiment_trend(segments)
    objections = detect_objections(segments)
    buying_signals = detect_buying_signals(segments)
    engagement = engagement_level(segments)
    recommendations = recommend_actions(objections, buying_signals, trend)

    return {
        "mode": "sales",
        "summary": {
            "overall_call_sentiment": call_sentiment,
            "sentiment_trend": trend,
            "engagement_level": engagement
        },
        "objections": objections,
        "buying_signals": buying_signals,
        "recommended_actions": recommendations,
        "key_moments": key_moments(objections, buying_signals),
        "transcript": [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "sentiment": s["sentiment"], # Keep numeric score if needed for frontend, or map to label
                "sentiment_label": s.get("sentiment_label", "Neutral"), # Ensure label is passed back
                "confidence": s["sentiment_confidence"]
            }
            for s in segments
        ]
    }

