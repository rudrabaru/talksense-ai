import sys
import os
from collections import Counter

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

# --- EXECUTIVE SIGNAL EXTRACTORS ---

# Controlled Vocabulary for Topics
TOPIC_KEYWORDS = {
    "onboarding": ["onboarding", "training", "getting started", "account", "signup"],
    "usability": ["usability", "user experience", "ux", "interface", "click", "navigation"],
    "documentation": ["documentation", "docs", "manual", "guide", "readme"],
    "client_feedback": ["feedback", "complaint", "issue", "review", "customer"],
    "performance": ["slow", "latency", "speed", "performance", "crash"],
    "pricing": ["pricing", "cost", "budget", "expensive", "cheap"]
}

STRONG_ACTION_VERBS = ["will", "assign", "finalize", "implement", "ship", "update", "create", "deploy"]
# Weak verbs are implicitly anything not strong, but listed for clarity/future use
WEAK_ACTION_VERBS = ["maybe", "should", "probably", "look into", "discuss", "consider", "might"]

def extract_primary_topic(segments):
    """
    Extracts topic using controlled vocabulary buckets.
    Falls back to 'general discussion' if no bucket matches.
    """
    scores = {k: 0 for k in TOPIC_KEYWORDS}

    for seg in segments:
        text = seg.get("text", "").lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(k in text for k in keywords):
                scores[topic] += 1

    # Find the topic with the max score
    if not scores: # Safety check
        return "general discussion"
        
    top_topic = max(scores, key=scores.get)
    
    # If no keywords were found (score is 0), return fallback
    if scores[top_topic] == 0:
        return "general discussion"

    return top_topic.replace("_", " ")

def assess_decision_state(decisions):
    if not decisions:
        return "no final decision"
    return "decision made"

def assess_action_clarity(action_items):
    """
    Assesses action clarity by filtering for STRONG commitments.
    Weak suggestions do not count as 'next steps identified'.
    """
    strong_actions = [
        a for a in action_items
        if any(v in a["task"].lower() for v in STRONG_ACTION_VERBS)
    ]

    if strong_actions:
        return "next steps identified"
        
    return "no clear next steps"

def assess_risk_level(tension_points, sentiment_counts):
    total = sum(sentiment_counts.values())
    neg_ratio = sentiment_counts["Negative"] / total if total > 0 else 0
    
    if len(tension_points) > 0 or neg_ratio > 0.3:
        return "elevated"
    if sentiment_counts["Negative"] > sentiment_counts["Positive"]:
        return "moderate"
    return "low"

def compose_executive_summary(signals):
    """
    Composes a dense executive summary paragraph from signals.
    Includes guardrails for low-confidence topics.
    """
    topic = signals["topic"]
    decision = signals["decision_state"]
    action = signals["action_clarity"]
    risk = signals["risk"]
    
    # GUARDRAIL: Refuse to be specific if topic is generic
    if topic in ["general discussion", "misc"]:
        topic_phrase = "key issues"
    else:
        topic_phrase = topic

    summary_parts = []
    
    # Part 1: Topic & Risk Context
    if risk == "elevated":
        summary_parts.append(f"The discussion centered on {topic_phrase} and surfaced unresolved concerns.")
    elif risk == "moderate":
        summary_parts.append(f"The discussion regarding {topic_phrase} was mixed, with some points requiring attention.")
    else:
        summary_parts.append(f"The team discussed {topic_phrase} with no major blockers identified.")
        
    # Part 2: Decisions & Actions (CALIBRATED LOGIC)
    
    # Case: Indecision + No Action + Risk -> Emphasize Stagnation/Risk
    if decision == "no final decision" and action == "no clear next steps":
        if risk != "low":
            summary_parts.append("Discussions remain open, and the lack of clear next steps poses a risk to progress.")
        else:
            summary_parts.append("No final decisions were made, and future actions need to be clarified.")
            
    # Case: Decision Made + Actions
    elif decision == "decision made" and action == "next steps identified":
        summary_parts.append("Key decisions were locked in, and clear next steps have been assigned.")
        
    # Case: Decision Made + No Actions
    elif decision == "decision made" and action == "no clear next steps":
        summary_parts.append("Decisions were reached, but specific follow-up actions remain undefined.")
        
    # Case: No Decision + Strong Actions (Unusual but possible - "Let's explore X")
    elif decision == "no final decision" and action == "next steps identified":
        summary_parts.append("While no final consensus was reached, action items were set to drive progress.")
    
    # Fallback
    else:
        summary_parts.append("Future actions need to be defined to move forward.")
        
    return " ".join(summary_parts)

# --- BUSINESS SENTIMENT ENGINE ---

EXECUTION_TERMS = [
    "bug", "issue", "qa", "approval", "dependency",
    "delay", "fix", "blocker", "work out", "details"
]

BUSINESS_NEUTRAL_TERMS = [
    "important", "agenda", "action list",
    "roles", "plan", "next meeting",
    "presentation", "schedule", "minutes",
    "discussion", "update", "strategy"
]

EMOTIONAL_NEGATIVE_TERMS = [
    "frustrated", "angry", "unacceptable",
    "disappointed", "annoyed", "conflict",
    "argue", "blame", "failure"
]

RESOLUTION_TERMS = [
    "fixed", "on track", "confirmed",
    "none", "no problem", "no blockers",
    "i will", "we will", "ready",
    "agreed", "locked"
]

# --- MEETING HEALTH ENGINE ---

# Simple temporal keywords to infer timeline if explicit field is missing
TEMPORAL_KEYWORDS = [
    "tomorrow", "next week", "monday", "tuesday", "wednesday", "thursday", "friday",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "by EOD", "by end of day", "deadline", "due", "schedule"
]

def is_controlled(item):
    """
    Control Check: Does the item have an owner AND a timeline?
    A dependency is SAFE if it is controlled.
    """
    has_owner = item.get("owner") and item["owner"] != "Unassigned"
    has_timeline = item.get("timeline") or item.get("deadline") != "Not specified"
    
    # Fallback: Check text for timeline keywords if not explicit
    if not has_timeline:
        text = item.get("task", "").lower()
        has_timeline = any(t in text for t in TEMPORAL_KEYWORDS)
        
    return has_owner and has_timeline

def detect_explicit_no_blockers(segments):
    """
    Scans the last 10 segments for explicit 'No Blockers' statements.
    'Any blockers? None.'
    """
    if not segments:
        return False
        
    tail = segments[-10:]
    for seg in tail:
        text = seg.get("text", "").lower()
        # "none" is risky alone, but "no blockers" is safe.
        # "any blockers? none" implies detection of question answer pair logic 
        # which is hard with just looking at single segments, but let's try strict keywords for now.
        if "no blocker" in text or ("none" in text and "blocker" in text): 
             # Simplistic: "none for me re: blockers"
             return True
        # Check for specific "Any blockers?" -> "None" question/answer pattern requires context, 
        # but let's assume specific phrases like "no impediments", "all clear".
        if "all clear" in text or "good to go" in text:
            return True
            
    return False

def adjust_segment_sentiment(text, raw_score):
    """
    Adjusts sentiment score based on business context.
    - Emotional terms -> Real Negativity.
    - Business Neutral -> Force 0.0.
    - Execution terms -> Downweight if not resolved.
    - Resolution + Execution -> Neutral/Positive.
    """
    text_lower = text.lower()
    
    # 1. Check for True Emotional Negativity (Highest Priority)
    if any(t in text_lower for t in EMOTIONAL_NEGATIVE_TERMS):
        return raw_score

    # 2. Check for Business Neutrality
    if any(t in text_lower for t in BUSINESS_NEUTRAL_TERMS):
        return 0.0

    # 3. Check for Execution Context
    has_execution = any(t in text_lower for t in EXECUTION_TERMS)
    has_resolution = any(r in text_lower for r in RESOLUTION_TERMS)

    if has_execution:
        if has_resolution:
            # Resolution flips execution mentions to at least Neutral (+ small boost)
            return max(0.0, raw_score) + 0.1
        else:
            # Execution without resolution: Downgrade negativity
            # "We have a bug" is work, not emotional crisis
            if raw_score < 0:
                return raw_score * 0.3 # Heavily downweight negativity
    
    return raw_score

def calculate_business_sentiment(segments, meeting_health):
    """
    Calculates the overall 'Business Sentiment' score and label.
    1. Adjusts individual segment scores.
    2. Weights the end of the meeting.
    3. Applies Outcome Override.
    """
    if not segments:
        return 0, "Neutral / Focused"

    adjusted_scores = []
    for s in segments:
        raw_score = s.get("sentiment_score", 0) # Assumes nlp_engine provides this
        # Fallback if sentiment_score missing (e.g. from labels)
        if "sentiment_score" not in s:
            # Map label to score approximation if needed
            label = s.get("sentiment", "Neutral")
            raw_score = 0.5 if label == "Positive" else -0.5 if label == "Negative" else 0
            
        adj_score = adjust_segment_sentiment(s.get("text", ""), raw_score)
        adjusted_scores.append(adj_score)

    # Base Average (Corrected: Average of ADJUSTED scores)
    avg_score = sum(adjusted_scores) / len(adjusted_scores) if adjusted_scores else 0

    # End State Adjustment
    end_boost = ending_state_boost(segments)
    
    final_score = avg_score + end_boost

    # Outcome Override (The "Good" Gate)
    # If meeting is On Track, sentiment cannot be broadly Negative
    if meeting_health == "on_track" and final_score < -0.1:
        final_score = 0.0

    # Determine Label
    if final_score > 0.3:
        label = "Positive"
    elif final_score < -0.3:
        label = "Tense"
    else:
        label = "Neutral / Focused"

    return final_score, label

# --- EXISTING HELPERS ---

def outcome_override(decisions, action_items, tension_points):
    """
    Strong Outcome Signals trump negative sentiment.
    If Decisions + Assigned Actions + No Blockers -> GOOD.
    """
    has_decisions = len(decisions) > 0
    has_assigned_actions = any(a["owner"] != "Unassigned" for a in action_items)
    is_blocked = len(tension_points) > 0

    if has_decisions and has_assigned_actions and not is_blocked:
        return True
    return False

def ending_state_boost(segments):
    """
    Checks the last 5 segments for positive closure/no blockers.
    Returns a sentiment boost factor.
    """
    if not segments:
        return 0
    
    tail = segments[-5:]
    # Check for closure language
    for seg in tail:
        text = seg.get("text", "").lower()
        if any(k in text for k in ["no blocker", "no blockers", "good to go"]):
             return 0.3
        if "agreed" in text:
             return 0.2
    return 0

def evaluate_meeting_health(decisions, action_items, tension_points, sentiment_counts, segments):
    """
    Revised Health Logic: Control > Risk.
    Hierarchy: Blocked > At Risk > On Track.
    """
    # 1. Blockers Check (Unresolved Tension preventing progress)
    if tension_points:
        return "blocked"

    # 2. Dependencies Control Check
    # Filter actions that look like dependencies ("approval", "sign off", "dependency")
    dependencies = [
        a for a in action_items 
        if any(term in a["task"].lower() for term in ["approval", "sign off", "dependency", "qa"])
    ]
    
    for dep in dependencies:
        if not is_controlled(dep):
             # Uncontrolled Dependency -> Risk
             return "at_risk"

    # 3. Default -> On Track
    return "on_track"

# --- KEY INSIGHTS ENGINE ---

# Insight Priorities (Lower index = Higher priority)
INSIGHT_PRIORITY = [
    "Escalation Required",
    "Execution Risk",
    "Decision Ambiguity",
    "Ownership Gap",
    "Positive Momentum"
]

INSIGHT_TEMPLATES = {
    "Escalation Required": "Critical blockers in {topic} require immediate escalation.",
    "Execution Risk": "Potential execution risk identified in {topic} due to unclear next steps.",
    "Decision Ambiguity": "Key issues around {topic} were discussed, but no final decision was reached.",
    "Ownership Gap": "Follow-up actions related to {topic} lack clear ownership.",
    "Positive Momentum": "Clear progress made on {topic} with assigned actions and decisions."
}

def can_escalate(signals, tension_points, action_items, meeting_health):
    """
    Hard guardrail for Escalation Required.
    Escalate ONLY if: Explicit Blocker present AND Meeting Health is At Risk.
    """
    if meeting_health != "at_risk":
        return False

    if len(tension_points) == 0:
        return False
    
    # If explicit tension exists, check if it's resolved by actions
    has_assigned_actions = any(a["owner"] != "Unassigned" for a in action_items)
    
    if not has_assigned_actions:
        return True
        
    return False

def collapse_insights(insights):
    """
    Collapse overlapping insights to the most informative one.
    Execution Risk > Decision Ambiguity.
    """
    types = {i["type"] for i in insights}

    if "Execution Risk" in types and "Decision Ambiguity" in types:
        insights = [i for i in insights if i["type"] != "Decision Ambiguity"]

    return insights

def generate_key_insights(signals, action_items, decisions, tension_points, meeting_health):
    """
    Generates structured insights based on strict signal combinations.
    Conservative generation: Max 2 insights.
    SUPPRESSES risks if meeting_health is 'good' (On Track).
    """
    insights = []
    topic = signals.get("topic", "general discussion")
    if topic == "general discussion":
        topic = "key initiatives" 

    is_on_track = meeting_health == "good"

    # 1. Decision Ambiguity
    if not is_on_track and signals["decision_state"] == "no final decision" and topic != "key initiatives":
        insights.append({
            "type": "Decision Ambiguity",
            "text": INSIGHT_TEMPLATES["Decision Ambiguity"].format(topic=topic),
            "signals": ["no_decisions", "active_topic"],
            "_confidence": 0.8
        })

    # 2. Execution Risk
    # Suppress if On Track
    strong_actions_exist = signals["action_clarity"] == "next steps identified"
    raw_actions_exist = len(action_items) > 0
    
    if not is_on_track and raw_actions_exist and not strong_actions_exist:
        insights.append({
            "type": "Execution Risk",
            "text": INSIGHT_TEMPLATES["Execution Risk"].format(topic=topic),
            "signals": ["weak_action_verbs", "no_strong_actions"],
            "_confidence": 0.85
        })

    # 3. Ownership Gap
    # Suppress if On Track
    if raw_actions_exist:
        unassigned_count = sum(1 for a in action_items if a["owner"] == "Unassigned")
        if unassigned_count == len(action_items):
             insights.append({
                "type": "Ownership Gap",
                "text": INSIGHT_TEMPLATES["Ownership Gap"].format(topic=topic),
                "signals": ["actions_exist", "all_owners_unassigned"],
                "_confidence": 0.9
            })

    # 4. Escalation Required
    # Must use updated can_escalate that checks health
    if can_escalate(signals, tension_points, action_items, meeting_health):
        insights.append({
            "type": "Escalation Required",
            "text": INSIGHT_TEMPLATES["Escalation Required"].format(topic=topic),
            "signals": ["elevated_risk", "tension_detected"],
            "_confidence": 0.95
        })

    # 5. Positive Momentum
    if is_on_track or (signals["decision_state"] == "decision made" and strong_actions_exist):
         insights.append({
            "type": "Positive Momentum",
            "text": INSIGHT_TEMPLATES["Positive Momentum"].format(topic=topic),
            "signals": ["decision_made", "strong_actions"],
            "_confidence": 0.85
        })

    # Collapse Overlaps (Risk > Ambiguity)
    insights = collapse_insights(insights)

    # SORT & FILTER
    insights.sort(key=lambda x: INSIGHT_PRIORITY.index(x["type"]) if x["type"] in INSIGHT_PRIORITY else 99)
    
    return insights[:2]


def detect_tension_points(segments):
    """
    Detect tense or unresolved moments in a meeting.
    Heuristic-based (hackathon-safe).
    """
    tension_points = []

    for seg in segments:
        sentiment = seg.get("sentiment", 0)
        confidence = seg.get("sentiment_confidence", 0)
        text = seg.get("text", "").lower()

        # Strong negative sentiment with confidence
        if sentiment < -0.4 and confidence >= 0.6:
            tension_points.append({
                "text": seg["text"],
                "time": seg["start"],
                "reason": "Negative sentiment"
            })
            continue

        # Explicit tension keywords (fallback)
        if any(k in text for k in ["blocked", "issue", "problem", "concern", "delay"]):
            tension_points.append({
                "text": seg["text"],
                "time": seg["start"],
                "reason": "Potential blocker or concern"
            })

    return tension_points


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

    # 5.3 Sentiment Aggregation (Core Signal)
    sentiment_counts = aggregate_sentiment(segments)
    
    # 5.5 Detect Decisions Made
    decisions = detect_decisions(segments)

    # 5.6 Detect Action Items
    action_items = detect_action_items(segments)

    # 5.7 Detect Tension / Unresolved Moments
    tension_points = detect_tension_points(segments)

    # --- NEW: EXECUTIVE SIGNAL GENERATION ---
    signals = {
        "topic": extract_primary_topic(segments),
        "decision_state": assess_decision_state(decisions),
        "action_clarity": assess_action_clarity(action_items),
        "risk": assess_risk_level(tension_points, sentiment_counts)
    }

    # --- 1. OVERRIDES (NO BLOCKERS) ---
    # Determine explicit "No Blockers"
    no_blockers_declared = detect_explicit_no_blockers(segments)
    
    # If explicit no blockers, WIPE tension points designated as "Potential blocker"
    # But keep specific "Negative sentiment" ones if they are strong? 
    # User said: "if explicit_no_blockers: blockers = []"
    actual_blockers = tension_points[:]
    if no_blockers_declared:
        actual_blockers = []

    # --- 2. MEETING HEALTH EVALUATION ---
    # Pass corrected blockers list
    meeting_health = evaluate_meeting_health(decisions, action_items, actual_blockers, sentiment_counts, segments)
    
    # --- 3. BUSINESS SENTIMENT ---
    # Calculates Adjusted Score + Label (Neutral/Focused)
    biz_sentiment_score, biz_sentiment_label = calculate_business_sentiment(segments, meeting_health)

    # --- 4. KEY INSIGHTS GENERATION (With Outcome Override) ---
    key_insights = generate_key_insights(signals, action_items, decisions, actual_blockers, meeting_health)
    
    # 5.4 Generate Meeting Summary (SIGNAL-BASED)
    summary = compose_executive_summary(signals)

    # 5.8 Build Final Meeting Output
    return {
        "mode": "meeting",
        "summary": summary,
        "executive_signals": signals,
        "meeting_health": meeting_health,
        "key_insights": key_insights,
        "overall_sentiment_label": biz_sentiment_label, # Use NEW Business Label
        "sentiment_score": biz_sentiment_score, # Pass score for UI badge color mapping if needed
        "sentiment_overview": sentiment_counts,
        "decisions": decisions,
        "action_items": action_items,
        "tension_points": actual_blockers, # Return the effective list
        "blockers_present": len(actual_blockers) > 0,
        "dependencies_controlled": meeting_health != "at_risk",
        "transcript": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "sentiment": seg["sentiment"],
                "confidence": seg.get("sentiment_confidence", 0)
            }
            for seg in segments
        ]
    }
def detect_decisions(segments):
    """
    Detect decisions made during a meeting.
    Rule-based using configured decision keywords.
    """
    decisions = []

    for seg in segments:
        text = seg.get("text", "").lower()
        confidence = seg.get("sentiment_confidence", 0)

        if any(k in text for k in DECISION_KEYWORDS) and confidence >= 0.5:
            decisions.append({
                "text": seg["text"],
                "time": seg["start"]
            })

    return decisions


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

