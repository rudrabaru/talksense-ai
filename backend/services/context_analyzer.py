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

def aggregate_sentiment(segments):
    counts = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 0
    }

    for seg in segments:
        label = seg.get("sentiment_label", "Neutral")
        if label in counts:
            counts[label] += 1

    return counts

def generate_meeting_summary(segments, sentiment_counts):
    total = sum(sentiment_counts.values())
    if total == 0:
        return "The meeting was largely informational."

    neg_ratio = sentiment_counts["Negative"] / total
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

def analyze_meeting(nlp_input: dict) -> dict:
    """
    Main entry point for Meeting Mode analysis.
    Requested: Summary, Key Insights/Decisions, Action Items, Transcript
    """
    enriched_segments = nlp_input.get("segments", [])
    segments = sorted(enriched_segments, key=lambda x: x["start"])

    sentiment_counts = aggregate_sentiment(segments)
    summary = generate_meeting_summary(segments, sentiment_counts)
    decisions = detect_decisions(segments)
    action_items = detect_action_items(segments)

    return {
        "mode": "meeting",
        "summary": summary,
        "decisions": decisions, # Key insights or Decisions Made
        "action_items": action_items,
        "transcript": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "sentiment": seg["sentiment"],
                "sentiment_label": seg.get("sentiment_label", "Neutral"),
                "confidence": seg.get("sentiment_confidence", 0)
            }
            for seg in segments
        ]
    }


# --- SALES MODE HELPERS ---

def overall_call_sentiment(segments):
    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    for seg in segments:
        if seg["sentiment_confidence"] >= 0.6:
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

def recommend_actions(objections):
    actions = []

    if any(o["type"] == "Pricing" for o in objections):
        actions.append("Send pricing clarification")

    if any(o["type"] == "Authority" for o in objections):
        actions.append("Follow up after internal discussion")

    # Fallback/Generic
    if not actions:
        actions.append("Schedule follow-up call")

    return list(set(actions))

def analyze_sales(enriched_segments: list) -> dict:
    """
    Main entry point for Sales Mode analysis.
    Requested: Overall Sentiment, Objections, Recommended Actions, Transcript
    """
    if not enriched_segments:
        return {
            "mode": "sales",
            "overall_call_sentiment": "neutral",
            "objections": [],
            "recommended_actions": [],
            "transcript": []
        }

    segments = sorted(enriched_segments, key=lambda x: x["start"])

    call_sentiment = overall_call_sentiment(segments)
    objections = detect_objections(segments)
    recommendations = recommend_actions(objections)

    return {
        "mode": "sales",
        "overall_call_sentiment": call_sentiment,
        "objections": objections,
        "recommended_actions": recommendations,
        "transcript": [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "sentiment": s["sentiment"],
                "sentiment_label": s.get("sentiment_label", "Neutral"),
                "confidence": s["sentiment_confidence"]
            }
            for s in segments
        ]
    }

