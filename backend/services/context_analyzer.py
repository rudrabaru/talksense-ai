import sys
import os
from collections import Counter

# Ensure we can import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import KEYWORDS_CONFIG

# Load Configured Keywords (or defaults)
DECISION_KEYWORDS = KEYWORDS_CONFIG["meeting"]["decisions"]
ACTION_KEYWORDS = KEYWORDS_CONFIG["meeting"]["actions"]

# --- NEW: INDEPENDENT DETECTOR KEYWORDS ---
OWNERSHIP_COMMITMENT_KEYWORDS = KEYWORDS_CONFIG["meeting"]["ownership_commitment"]
DIRECTIONAL_DECISION_KEYWORDS = KEYWORDS_CONFIG["meeting"]["directional_decisions"]
ISSUE_KEYWORDS = KEYWORDS_CONFIG["meeting"]["issues"]
RISK_KEYWORDS = KEYWORDS_CONFIG["meeting"]["risks"]

# --- STREAMLINED CONSTANTS ---
DECISION_PATTERNS = [
    "let's lock", "we will", "we'll", "decision is", "we decided",
    "we are going to", "tentative release", "agreed", "go with", "lock it"
]

OWNERSHIP_PATTERNS = [
    "i will", "i'll", "i am going to", "i can",
    "i'll take", "i'll handle", "i'll follow up", "i'll confirm",
    "i'll inform", "we will", "we'll"
]

EXECUTION_VERBS = [
    "deploy", "launch", "release", "ship", "schedule",
    "present", "assign", "monitor", "fix", "optimize",
    "confirm", "inform", "notify", "coordinate", "follow up", "check"
]

CONCEPTUAL_VERBS = [
    "pitch", "position", "idea", "think", "discuss", "explore", "believe",
    "maybe", "might", "could", "option", "brainstorm", "possibility"
]

WINDOW = 3

# Agenda blacklist - exclude non-decision statements
AGENDA_PHRASES = [
    "goal today",
    "objective of",
    "purpose of",
    "agenda",
    "today is to",
    "meeting is to",
    "we are here to",
    "main goal",
    "focus today"
]

# Negative-form decisions - declarative rejections
NEGATIVE_DECISION_PATTERNS = [
    "let's not delay",
    "do not delay",
    "we will not delay",
    "no need to delay",
    "not delaying",
    "won't delay",
    "keep the plan",
    "stick with",
    "no change"
]

# --- SALES MODE HELPERS ---
OBJECTION_KEYWORDS = KEYWORDS_CONFIG["sales"]["objections"]

NO_INTENT_TERMS = [
    "not planning to switch", "not switching", "not this quarter",
    "later this year", "maybe later", "happy with current",
    "already using", "just exploring", "no budget",
    "not a priority", "no urgency", "not interested"
]

DEFER_TERMS = [
    "later this year", "few months",
    "next quarter", "sometime later"
]

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

# --- STEP 1: INDEPENDENT DETECTORS (NO SENTIMENT) ---

def detect_ownership_committed(segments):
    """
    Detects commitment language patterns.
    Returns True if ANY speaker commits to an action.
    MANDATORY: Ownership is NOT just keywords like "owner".
    """
    for seg in segments:
        text = seg.get("text", "").lower()
        # Check for commitment patterns
        if any(pattern in text for pattern in OWNERSHIP_COMMITMENT_KEYWORDS):
            return True
    return False

def detect_decisions_made(segments):
    """
    Detects directional commitments.
    Returns True if any direction is set.
    NOT just looking for "decided" - includes "we will", "next step is", etc.
    """
    for seg in segments:
        text = seg.get("text", "").lower()
        # Check for directional decision patterns
        if any(pattern in text for pattern in DIRECTIONAL_DECISION_KEYWORDS):
            return True
    return False

def detect_signals(segments):
    """
    FROZEN: Single-pass signal detection.
    🔒 HARD FREEZE: execution_decision is set once and NEVER changed.
    No re-evaluation. No confidence downgrade. No "but maybe".
    
    Binary signals:
    - Either it happened OR it didn't
    - Strength is a UI concern, not a logic concern
    """
    ownership_detected = False
    decision_detected = False
    execution_decision_detected = False

    for seg in segments:
        text = seg.get("text", "")

        # Check for ownership patterns
        if not ownership_detected and any(p in text.lower() for p in OWNERSHIP_PATTERNS):
            ownership_detected = True

        # Check for decisions (for display purposes)
        if not decision_detected and any(d in text.lower() for d in DECISION_PATTERNS):
            decision_detected = True

        # 🔒 HARD FREEZE: Check for execution decision
        # Once TRUE, break immediately - no further evaluation
        if not execution_decision_detected and is_valid_execution_decision(text):
            execution_decision_detected = True
            # FREEZE: Do NOT allow later logic to change this back
            # No re-evaluation, no confidence downgrade, no "but maybe"

    return {
        "ownership": ownership_detected,
        "decision": decision_detected,
        "execution_decision": execution_decision_detected
    }

def detect_execution_attempted(segments):
    """
    🎯 STEP 1: NEW SIGNAL - Execution attempted detection
    
    Execution attempted = concrete execution verbs discussed,
    NOT just ownership or alignment.
    
    This checks if the conversation included actual execution-related
    discussions, not just preparatory or strategic talk.
    """
    for seg in segments:
        t = seg.get("text", "").lower()
        if any(v in t for v in EXECUTION_VERBS):
            return True
    return False

def detect_issues_present(segments):
    """
    Non-punitive issue detection.
    Returns True if issues mentioned (signal only, not penalty).
    """
    for seg in segments:
        text = seg.get("text", "").lower()
        if any(pattern in text for pattern in ISSUE_KEYWORDS):
            return True
    return False

def detect_risks_present(segments):
    """
    Non-punitive risk detection.
    Returns True if risks mentioned (signal only, not penalty).
    """
    for seg in segments:
        text = seg.get("text", "").lower()
        if any(pattern in text for pattern in RISK_KEYWORDS):
            return True
    return False

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

# --- EXECUTIVE SUMMARY ENGINE ---

def classify_issue(issue):
    """
    Classifies an issue as 'controlled' or 'uncontrolled'.
    Control = Owner AND Timeline.
    """
    # If the issue object already has owner/deadline structure (like an action item)
    if "owner" in issue and "deadline" in issue:
        has_owner = issue["owner"] != "Unassigned"
        has_timeline = issue["deadline"] != "Not specified"
        return "controlled" if has_owner and has_timeline else "uncontrolled"
    
    # If it's a raw tension point (unstructured)
    # By definition, raw tension points lack control unless explicitly resolved
    return "uncontrolled"

def get_uncontrolled_issues(issues, action_items):
    """
    Identifies truly uncontrolled issues.
    1. Uncontrolled Action Items (Dependencies/Fixes without owner/time).
    2. Unresolved Tension Points (Blockers not wiped by overrides).
    """
    uncontrolled = []
    
    # Check Action Items that are "Issues" (Execution/Fixes)
    for action in action_items:
        text = action.get("task", "").lower()
        if any(t in text for t in EXECUTION_TERMS):
            if classify_issue(action) == "uncontrolled":
               uncontrolled.append(action)

    # Check Tension Points (Blockers)
    # These are already filtered by 'no blockers' override in main flow
    for issue in issues:
         uncontrolled.append(issue) # Raw tension points are uncontrolled by default
         
    return uncontrolled

def assess_meeting_quality(decisions, uncontrolled_issues, explicit_no_blockers):
    """
    Computes Meeting Quality strictly from outcomes.
    """
    has_decisions = len(decisions) > 0
    has_issues = len(uncontrolled_issues) > 0
    
    if has_decisions and not has_issues:
        return "good"
    elif has_issues:
        # If explicitly said "no blockers", downgrade severity? 
        # But 'uncontrolled_issues' logic should handle that upstream.
        return "needs_attention"
    else:
        # No decisions, no issues -> Neutral
        return "neutral"

def compose_executive_summary(signals, decisions, action_items, tension_points, explicit_no_blockers):
    """
    Generates Executive Summary using strict Case A/B/C templates.
    """
    topic = signals.get("topic", "key initiatives")
    if topic == "general discussion": topic = "key initiatives"
    
    # 1. Normalize & Classify
    uncontrolled_issues = get_uncontrolled_issues(tension_points, action_items)
    quality = assess_meeting_quality(decisions, uncontrolled_issues, explicit_no_blockers)
    
    # 2. Hard Gate: Forbid concern language if no uncontrolled issues
    forbid_concern = len(uncontrolled_issues) == 0

    # 3. Select Template
    summary = ""
    
    # Case A (GOOD): Decisions + No Uncontrolled Issues
    if quality == "good":
        summary = (
            f"The discussion focused on {topic}, with key decisions locked in and clear next steps assigned. "
            "Minor issues were identified with ownership and resolution plans in place."
        )
        # End State Override: Boost tone if strictly positive end
        if explicit_no_blockers:
             summary = summary.replace("Minor issues were identified", "Execution details were addressed")

    # Case B (ATTENTION): Decisions + Uncontrolled Issues
    elif quality == "needs_attention" and len(decisions) > 0:
        summary = (
            f"The discussion addressed {topic} and resulted in decisions, but some issues remain unresolved and require follow-up."
        )

    # Case C (POOR): No Decisions + Uncontrolled Issues (or Neutral with Issues)
    elif quality == "needs_attention":
        summary = (
             f"The discussion surfaced unresolved concerns regarding {topic} without clear decisions or ownership, indicating potential risk."
        )
        
    # Case D (NEUTRAL): No Decisions + No Issues (Status Check)
    else:
        summary = (
            f"The team discussed {topic}. Future actions need to be defined to move forward."
        )

    return summary

def compose_executive_summary_v2(meeting_quality, execution_attempted):
    """
    🎯 STEP 3: GATE EXECUTIVE SUMMARY by execution_attempted
    
    LOCKED: Executive Summary (quality-driven, not transcript-driven).
    NON-INTERPRETIVE: No injected decisions, blockers, or sentiment.
    
    CRITICAL FIX:
    - Medium quality doesn't automatically mean execution failure
    - Check execution_attempted to determine context
    """
    quality_label = meeting_quality["label"]
    
    if quality_label == "High":
        return (
            "Clear execution decisions were made, with ownership assigned "
            "and concrete next steps defined."
        )
    elif quality_label == "Medium":
        # 🎯 THE FIX: Check if execution was even attempted
        if execution_attempted:
            return (
                "Some execution elements were discussed, but follow-up clarity "
                "is still required."
            )
        else:
            return (
                "The team discussed strategy and direction. "
                "Execution planning will continue in follow-up discussions."
            )
    else:
        return (
            "The discussion lacked clear decisions or ownership, "
            "limiting execution progress."
        )


# --- STEP 2 & 3: NEW QUALITY ENGINE (SENTIMENT-FREE) ---

def compute_meeting_quality_v2(signals):
    """
    🔒 FINAL FROZEN DEFINITION - DO NOT MODIFY
    
    Meeting Quality = ONLY ownership + execution_decision
    
    Returns ONLY label (no score, no drivers, no side effects)
    This is the ONLY definition that preserves old outputs.
    """
    ownership = signals.get("ownership", False)
    execution = signals.get("execution_decision", False)

    if ownership and execution:
        return {"label": "High"}

    if ownership or execution:
        return {"label": "Medium"}

    return {"label": "Low"}

def compute_project_risk(issues_detected, risks_detected, uncontrolled_dependencies):
    """
    STEP 7: Separate "Meeting Quality" from "Project Risk".
    Computes Project Risk independently from meeting quality.
    This is about the PROJECT, not the MEETING.
    """
    risk_score = 0
    drivers = []
    
    if issues_detected:
        risk_score += 3
        drivers.append("Issues identified")
    
    if risks_detected:
        risk_score += 3
        drivers.append("Risks flagged")
    
    if uncontrolled_dependencies:
        risk_score += 4
        drivers.append("Uncontrolled dependencies")
    
    # Map score to label
    if risk_score >= 7:
        label = "High"
    elif risk_score >= 4:
        label = "Medium"
    else:
        label = "Low"
    
    return {
        "label": label,
        "score": risk_score,
        "drivers": drivers
    }

# --- OLD QUALITY ENGINE (DEPRECATED - KEPT FOR REFERENCE) ---

def compute_meeting_quality(signals, decisions, action_items, tension_points, explicit_no_blockers):
    """
    OLD VERSION - DEPRECATED
    This function is kept for backward compatibility but should not be used.
    Use compute_meeting_quality_v2 instead.
    """
    score = 0
    drivers = []
    
    # 1. Decisions (+2)
    if signals.get("decision_state") == "decision made":
        score += 2
        drivers.append("Decisions finalized")
        
    # 2. Ownership (+2)
    has_owners = any(a["owner"] != "Unassigned" for a in action_items)
    if has_owners:
        score += 2
        drivers.append("Ownership assigned")
        
    # 3. Timeline (+2)
    # Check if any action has a specific deadline (not "Not specified")
    has_timeline = any(a["deadline"] != "Not specified" for a in action_items)
    if has_timeline:
        score += 2
        drivers.append("Timeline defined")
        
    # 4. Blockers Cleared (+2)
    # Either explicit "no blockers" OR no detected tension points
    if explicit_no_blockers or not tension_points:
        score += 2
        drivers.append("No active blockers")
        
    # 5. Agenda Progression (+2)
    # If topic is specific (not general) and risk is not elevated
    if signals.get("topic") != "general discussion" and signals.get("risk") != "elevated":
        score += 2
        drivers.append("Agenda progressed")

    # --- GUARDRAILS ---
    # 1. No decisions + No owners -> Low (Max 4)
    if not decisions and not has_owners:
        score = min(score, 4)
        
    # 2. Decision + Owner + Timeline -> High (Min 8)
    if decisions and has_owners and has_timeline:
        score = max(score, 8)

    # Map to Label
    if score >= 8: label = "High"
    elif score >= 5: label = "Medium"
    else: label = "Low"
    
    return {
        "label": label,
        "score": score,
        "drivers": drivers
    }

def assess_sales_signals(segments, objections, recommendations):
    """
    Extracts binary signals for Sales Quality.
    """
    text_blob = " ".join([s["text"].lower() for s in segments])
    
    # 1. Decision Maker Identified
    # Heuristic: "I decide", "my budget", "authorized", "decision maker"
    dm_terms = ["i decide", "my budget", "authorization", "sign the contract", "decision maker"]
    decision_maker = any(t in text_blob for t in dm_terms)
    
    # 2. Next Step Agreed
    # Strong recommendations exist OR explicit agreement
    next_step = len(recommendations) > 0 or any(t in text_blob for t in ["schedule next", "book a demo", "send the invite"])

    # 2b. Hard Commitment (NEW)
    # Strict list of booking confirmations
    HARD_COMMITMENT_TERMS = ["demo booked", "let’s schedule", "calendar invite", "meeting on tuesday"]
    hard_commitment = any(t in text_blob for t in HARD_COMMITMENT_TERMS)

    # 3. Disqualification Signal (Deal-Killer)
    no_intent = any(t in text_blob for t in NO_INTENT_TERMS)
    deferred = any(t in text_blob for t in DEFER_TERMS)
    
    # 4. Objection Addressed
    # If objections existed, were they followed by positive sentiment? 
    # Simplify: If objections exist but call sentiment is NOT negative -> Managed.
    objection_handled = False
    if objections:
        # Check sentiment of last 20% of call? 
        # For now, simplistic: if recommendations exist, we have a plan for them.
        objection_handled = True
    else:
        # No objections = implicit handling/clean
        objection_handled = True
        
    # 4. Value Articulated
    # Heuristic: "save", "roi", "benefit", "increase", "reduce cost"
    value_terms = ["save", "roi", "benefit", "increase revenue", "reduce cost", "efficiency"]
    value_articulated = any(t in text_blob for t in value_terms)
    
    # 5. Momentum (Not Stalled)
    # Stalled if "send info" is the ONLY outcome or sentiment is Negative
    stalled = "send info" in text_blob and not next_step
    
    return {
        "decision_maker_known": decision_maker,
        "next_step": next_step,
        "hard_commitment": hard_commitment,
        "no_intent": no_intent,
        "deferred": deferred,
        "objection_handled": objection_handled,
        "value_articulated": value_articulated,
        "stalled": stalled
    }

def compute_sales_quality(signals):
    """
    Computes Sales Quality Score (0-10).
    """
    score = 0
    drivers = []
    
    # 🔴 HARD DISQUALIFICATION OVERRIDE
    if signals.get("no_intent") or signals.get("deferred"):
        return {
            "label": "Low",
            "score": 2,
            "drivers": ["Disqualified: No Intent/Deferred"]
        }

    if signals["decision_maker_known"]:
        score += 2
        drivers.append("Decision maker identified")
        
    if signals["next_step"]:
        score += 3
        drivers.append("Next step agreed")

    if signals.get("hard_commitment"):
        score += 2
        drivers.append("Hard commitment locked")
        
    if signals["objection_handled"]:
        score += 2
        drivers.append("Objections managed")
        
    if signals["value_articulated"]:
        score += 2
        drivers.append("Value articulated")
        
    if not signals["stalled"]:
        score += 1
        drivers.append("Momentum maintained")
        
    # --- GUARDRAILS (UPDATED) ---
    # 1. High Quality = HARD COMMITMENT ONLY
    if signals.get("hard_commitment"):
        label = "High"
        score = max(score, 8) 
    # 2. Medium Quality = Next Step Agreed
    elif signals.get("next_step"):
        label = "Medium"
        score = max(score, 5)
    # 3. Low Quality = Everything else
    else:
        label = "Low"
        score = min(score, 4)
    
    return {
        "label": label,
        "score": score,
        "drivers": drivers
    }

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
    DEPRECATED: Legacy function - NOT used in v2 logic.
    Kept for backward compatibility only.
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

# DEPRECATED: Legacy constants - kept for backward compatibility only
# These are NOT used in v2 logic
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
    DEPRECATED: Legacy function - NOT used in v2 logic.
    Kept for backward compatibility only.
    """
    if meeting_health != "at_risk":
        return False

    if len(tension_points) == 0:
        return False
    
    has_assigned_actions = any(a["owner"] != "Unassigned" for a in action_items)
    
    if not has_assigned_actions:
        return True
        
    return False

def collapse_insights(insights):
    """
    DEPRECATED: Legacy function - NOT used in v2 logic.
    Kept for backward compatibility only.
    """
    types = {i["type"] for i in insights}

    if "Execution Risk" in types and "Decision Ambiguity" in types:
        insights = [i for i in insights if i["type"] != "Decision Ambiguity"]

    return insights

def generate_key_insights_v2(meeting_quality, execution_attempted):
    """
    🎯 STEP 4: GATE KEY INSIGHTS by execution_attempted (CRITICAL)
    
    FINAL VERSION: Key Insights Generator.
    🔒 TRUSTS SIGNALS BLINDLY - No re-scanning, no re-evaluation.
    
    CRITICAL FIX:
    - Medium quality doesn't automatically mean execution ambiguity
    - Check execution_attempted before inferring execution problems
    
    Rules:
    - Max 3 insights
    - No duplicate types
    - No transcript scanning
    - No assumptions
    - No uncertainty phrases
    - No "partial" execution inference without execution_attempted
    """
    insights = []
    q = meeting_quality["label"]

    if q == "High":
        insights.append({
            "type": "Positive Momentum",
            "text": "Clear execution decisions were made with ownership assigned."
        })

    elif q == "Medium":
        # 🎯 THE CRITICAL FIX: Check if execution was even attempted
        if execution_attempted:
            insights.append({
                "type": "Decision Ambiguity",
                "text": "Some execution elements remain unclear and require follow-up."
            })
        else:
            # NEW: Better insight for planning meetings
            insights.append({
                "type": "Strategic Planning",
                "text": "Direction and strategy were discussed. Detailed execution planning deferred to next meeting."
            })

    else:  # Low
        insights.append({
            "type": "Execution Risk",
            "text": "The meeting lacked clear decisions and ownership."
        })

    return insights[:3]


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

def extract_actions(segments):
    """
    FINAL: Extract execution-only actions.
    Hard rules:
    - First person
    - Future-oriented
    - MUST contain a real execution verb
    - MUST NOT be ownership-only
    """
    actions = []

    OWNERSHIP_ONLY_PHRASES = [
        "take ownership",
        "own this",
        "i'm responsible",
        "i am responsible"
    ]

    for seg in segments:
        text = seg.get("text", "")
        t = text.lower()

        # Must be first-person future
        if not (
            t.startswith("i will") or t.startswith("i'll")
            or t.startswith("we will") or t.startswith("we'll")
        ):
            continue

        # Must contain an execution verb
        if not any(v in t for v in EXECUTION_VERBS):
            continue

        # Must NOT be ownership-only
        if any(p in t for p in OWNERSHIP_ONLY_PHRASES):
            continue

        actions.append({
            "task": text,
            "owner": "Unassigned",
            "deadline": extract_deadline(text),
            "time": seg.get("start", 0)
        })

    return actions

def analyze_meeting(nlp_input: dict) -> dict:
    """
    STEP 9: Apply globally - Main entry point for Meeting Mode analysis.
    Uses new independent detectors and separates meeting_quality from project_risk.
    """
    summary = None # Default initialization
    
    enriched_segments = nlp_input.get("segments", [])
    segments = sorted(enriched_segments, key=lambda x: x["start"])

    # 🔒 STEP 5: LEGACY VERSION GUARD (CRITICAL for Backward Compatibility)
    # If this is a legacy audio, freeze execution_attempted to False
    # This ensures old stored audios NEVER change
    is_legacy = nlp_input.get("version") == "legacy"

    # 🔒 HARD FREEZE: Single-pass signal detection
    # Signals are computed ONCE and NEVER modified
    core_signals = detect_signals(segments)
    
    # Merge with legacy signals for backward compatibility
    signals = {
        **core_signals,
        "risk": detect_risks_present(segments),
        "issues": detect_issues_present(segments),
        "topic": extract_primary_topic(segments),
    }
    
    # 🔒 SIGNALS ARE NOW FROZEN - No function is allowed to modify them
    
    # 🎯 STEP 2: DETECT execution_attempted from EXECUTION_VERBS
    # This is NOT derived from ownership/execution_decision
    # It checks if concrete execution verbs were discussed
    # 🔒 LEGACY GUARD: Force False for legacy audios to freeze outputs
    if is_legacy:
        execution_attempted = False
    else:
        execution_attempted = detect_execution_attempted(segments)
    
    # 5.3 Sentiment Aggregation (Metadata Only - NOT used in quality)
    sentiment_counts = aggregate_sentiment(segments)
    
    # 5.5 Detect Decisions Made (Legacy - for action items display)
    decisions = detect_decisions(segments)
    signals["decision_state"] = "decision made" if signals["decision"] else "no final decision"

    # 5.6 Detect Action Items (STREAMLINED)
    action_items = extract_actions(segments)
    signals["action_clarity"] = "next steps identified" if action_items else "no clear next steps"

    # 5.7 Detect Tension / Unresolved Moments
    tension_points = detect_tension_points(segments)

    # --- 1. OVERRIDES (NO BLOCKERS) ---
    no_blockers_declared = detect_explicit_no_blockers(segments)
    
    actual_blockers = tension_points[:]
    if no_blockers_declared:
        actual_blockers = []

    # --- 2. MEETING HEALTH EVALUATION ---
    meeting_health = evaluate_meeting_health(decisions, action_items, actual_blockers, sentiment_counts, segments)
    
    # Check for uncontrolled dependencies
    uncontrolled_deps = meeting_health == "at_risk"
    
    # --- 3. BUSINESS SENTIMENT (Metadata Only) ---
    biz_sentiment_score, biz_sentiment_label = calculate_business_sentiment(segments, meeting_health)

    # 🔒 HARD FREEZE: Meeting quality computed ONCE from frozen signals
    # No function is allowed to modify it after this point
    # DO NOT TOUCH - Meeting Quality is already correct
    # The problem is interpretation, not scoring
    meeting_quality = compute_meeting_quality_v2(signals)
    
    # 🔍 STEP 6: SANITY CHECK (Uncomment to debug)
    # import logging
    # logger = logging.getLogger(__name__)
    # logger.info(f"🔍 QUALITY DEBUG: signals={signals}, meeting_quality={meeting_quality}")
    # logger.info(f"🔍 GUARANTEE: ownership={signals.get('ownership')}, execution={signals.get('execution_decision')}")
    # logger.info(f"🔍 RESULT: If ownership OR execution is True → Quality MUST be Medium or High")
    
    # --- STEP 7: PROJECT RISK SCORING ---
    project_risk = compute_project_risk(signals["issues"], signals["risk"], uncontrolled_deps)

    # 🎯 STEP 3: GATE EXECUTIVE SUMMARY by execution_attempted
    summary = compose_executive_summary_v2(meeting_quality, execution_attempted)

    # 🎯 STEP 4: GATE KEY INSIGHTS by execution_attempted (CRITICAL)
    key_insights = generate_key_insights_v2(meeting_quality, execution_attempted)
    
    # 🎯 STEP 5: HARD RULE for Action Plan
    # If execution was never attempted → no action plan
    if not execution_attempted:
        action_items = []
        decisions = []

    # Quality is locked - no downgrades, no overrides
    # If contradictions appear, the upstream logic needs fixing


    # --- Build Final Output ---
    return {
        "mode": "meeting",
        "meeting_quality": meeting_quality,  
        "project_risk": project_risk,        
        "summary": summary,
        "executive_signals": {**signals, "risk": "elevated" if (signals["issues"] or signals["risk"]) else "low"}, # Backwards compat
        "meeting_health": meeting_health,
        "key_insights": key_insights,
        "overall_sentiment_label": biz_sentiment_label, 
        "sentiment_score": biz_sentiment_score,
        "sentiment_overview": sentiment_counts,
        "decisions": decisions,
        "action_items": action_items,
        "tension_points": actual_blockers,
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
def is_question(text: str) -> bool:
    """
    Detect if text is a question.
    Questions are NEVER decisions.
    """
    t = text.strip().lower()
    return (
        t.endswith("?")
        or t.startswith("when ")
        or t.startswith("what ")
        or t.startswith("how ")
        or t.startswith("should ")
        or t.startswith("can ")
        or t.startswith("could ")
        or t.startswith("would ")
    )

def is_valid_decision(text: str) -> bool:
    """
    Validate if text is a real decision (not agenda/goal statement).
    OLD VERSION - Deprecated. Use is_valid_execution_decision instead.
    """
    t = text.lower()

    # Exclude agenda statements
    if any(a in t for a in AGENDA_PHRASES):
        return False

    # Must contain decision keyword
    return any(d in t for d in DECISION_KEYWORDS)

def is_valid_execution_decision(text: str) -> bool:
    """
    STRICT validation for execution decisions.
    Rejects: Questions, Agenda, Conceptual language.
    Accepts: Negative-form decisions (declarative rejections).
    """
    t = text.lower()

    if is_question(t):
        return False

    if any(a in t for a in AGENDA_PHRASES):
        return False

    if any(c in t for c in CONCEPTUAL_VERBS):
        return False

    if any(n in t for n in NEGATIVE_DECISION_PATTERNS):
        return True

    return any(d in t for d in DECISION_PATTERNS)

def detect_decisions(segments):
    """
    DEPRECATED: Legacy function - kept for DISPLAY ONLY.
    NOT used in quality computation logic.
    Detect execution decisions made during a meeting.
    STRICT filtering: Only declarative, execution-oriented decisions.
    """
    decisions = []

    for seg in segments:
        text = seg.get("text", "")
        
        # Apply STRICT validation filter
        if is_valid_execution_decision(text):
            decisions.append({
                "text": text,
                "time": seg.get("start", 0)
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

def compose_sales_summary(signals, quality):
    """
    Generates a sales-specific executive summary.
    Enforces explicit mention of disqualification if Low quality.
    """
    # 1. Disqualification Override
    if quality["label"] == "Low":
        if signals.get("no_intent"):
             return "The prospect indicated no plans to switch or lack of interest. The opportunity is currently not active."
        if signals.get("deferred"):
             return "The prospect signaled a deferral to a later timeline. The opportunity is currently paused."
        # Fallback Low
        return "The discussion concluded without clear next steps or momentum."

    # 2. High/Medium Summaries
    if quality["label"] == "High":
        return "Strong progress made with a hard commitment to next steps. The opportunity is advancing."
    
    # Medium
    return "The call generated soft momentum, but requires firmer commitment to next steps."

def generate_sales_insights(objections, signals, quality):
    """
    Generates structured key insights for sales calls.
    Similar structure to meeting insights but sales-focused.
    """
    insights = []
    
    # 1. Disqualification Signal (Highest Priority)
    if signals.get("no_intent") or signals.get("deferred"):
        insights.append({
            "type": "Execution Risk",
            "text": "Prospect indicated no immediate intent or deferred timeline. Opportunity may require re-qualification."
        })
        return insights[:3]  # Return early for disqualified leads
    
    # 2. Hard Commitment (Positive Momentum)
    if signals.get("hard_commitment"):
        insights.append({
            "type": "Positive Momentum",
            "text": "Hard commitment secured with confirmed next steps. Strong buying signal detected."
        })
    
    # 3. Objection Handling
    if objections:
        objection_types = list(set([o["type"] for o in objections]))
        if len(objection_types) > 2:
            insights.append({
                "type": "Execution Risk",
                "text": f"Multiple objection types raised ({', '.join(objection_types)}). Requires comprehensive follow-up strategy."
            })
        elif signals.get("objection_handled"):
            insights.append({
                "type": "Positive Momentum",
                "text": f"Objections around {', '.join(objection_types)} were addressed during the call."
            })
        else:
            insights.append({
                "type": "Decision Ambiguity",
                "text": f"Unresolved concerns regarding {', '.join(objection_types)} require follow-up."
            })
    
    # 4. Value Articulation
    if signals.get("value_articulated"):
        insights.append({
            "type": "Positive Momentum",
            "text": "Value proposition clearly communicated with ROI/benefit discussion."
        })
    else:
        insights.append({
            "type": "Ownership Gap",
            "text": "Value proposition not clearly established. Consider stronger ROI messaging in follow-up."
        })
    
    # 5. Next Steps
    if signals.get("next_step") and not signals.get("hard_commitment"):
        insights.append({
            "type": "Decision Ambiguity",
            "text": "Soft next step agreed but lacks firm commitment. Requires confirmation."
        })
    elif not signals.get("next_step"):
        insights.append({
            "type": "Execution Risk",
            "text": "No clear next steps defined. Follow-up strategy needed to maintain momentum."
        })
    
    # 6. Decision Maker
    if not signals.get("decision_maker_known"):
        insights.append({
            "type": "Ownership Gap",
            "text": "Decision maker not clearly identified. May need to engage additional stakeholders."
        })
    
    # Sort by priority and return top 3
    priority_order = ["Execution Risk", "Decision Ambiguity", "Ownership Gap", "Positive Momentum"]
    insights.sort(key=lambda x: priority_order.index(x["type"]) if x["type"] in priority_order else 99)
    
    return insights[:3]

def analyze_sales(enriched_segments: list) -> dict:
    """
    Main entry point for Sales Mode analysis.
    Requested: Overall Sentiment, Objections, Recommended Actions, Transcript
    """
    if not enriched_segments:
        return {
            "mode": "sales",
            "quality": {"label": "Low", "score": 0, "drivers": []},
            "overall_call_sentiment": "neutral",
            "sentiment_score": 0,
            "key_insights": [],
            "objections": [],
            "recommended_actions": [],
            "transcript": []
        }

    segments = sorted(enriched_segments, key=lambda x: x["start"])

    call_sentiment = overall_call_sentiment(segments)
    objections = detect_objections(segments)
    recommendations = recommend_actions(objections)
    
    # --- QUALITY SCORING ---
    sales_signals = assess_sales_signals(segments, objections, recommendations)
    
    # Map to Standard Signals for Centralized Quality Engine (Step 2 & 8)
    # This ensures "Logic lives in exactly one place"
    std_signals = {
        "ownership": sales_signals["decision_maker_known"] or sales_signals["next_step"],
        "execution_decision": sales_signals.get("hard_commitment", False),
        "decision": sales_signals["next_step"]
    }
    
    # Use centralized quality logic
    quality = compute_meeting_quality_v2(std_signals)

    # --- SUMMARY GENERATION ---
    summary = compose_sales_summary(sales_signals, quality)
    
    # --- KEY INSIGHTS GENERATION (NEW) ---
    key_insights = generate_sales_insights(objections, sales_signals, quality)
    
    # Calculate sentiment score from call_sentiment label
    sentiment_score_map = {
        "positive": 0.6,
        "mixed": 0.0,
        "negative": -0.6,
        "neutral": 0.0
    }
    sentiment_score = sentiment_score_map.get(call_sentiment, 0.0)

    return {
        "mode": "sales",
        "quality": quality, 
        "summary": summary,
        "overall_call_sentiment": call_sentiment,
        "sentiment_score": sentiment_score,
        "key_insights": key_insights,  # NEW: Structured insights
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


