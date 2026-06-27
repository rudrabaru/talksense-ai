"""
Intent Resolver — Sprint 3B Phase 4
Deterministic, offline, explainable clause-level intent classification.
No LLMs. No embeddings. No external APIs.
"""

# Intent labels
ACTION_ITEM = "ACTION_ITEM"
COMMITMENT = "COMMITMENT"
DECISION = "DECISION"
ROADMAP_STATEMENT = "ROADMAP_STATEMENT"
INFORMATION = "INFORMATION"
BUYING_SIGNAL = "BUYING_SIGNAL"
CONDITIONAL_INTEREST = "CONDITIONAL_INTEREST"
OBJECTION = "OBJECTION"
UNKNOWN = "UNKNOWN"

# ── ROADMAP_STATEMENT signals ────────────────────────────────────────────────
# "We will release new features next month" →  ROADMAP_STATEMENT
# Evidence: plural subject + product/feature noun + time-horizon noun
_ROADMAP_SUBJECTS = {
    "we will",
    "we'll",
    "we are going to",
    "the team will",
    "our team will",
    "the product will",
}
_ROADMAP_NOUNS = {
    "feature",
    "features",
    "update",
    "updates",
    "version",
    "release",
    "product",
    "platform",
    "app",
    "application",
    "module",
    "integration",
    "functionality",
    "capability",
    "capabilities",
    "improvement",
    "roadmap",
}
_ROADMAP_TIME_HORIZON = {
    "next month",
    "next quarter",
    "next year",
    "this quarter",
    "this year",
    "later this year",
    "q1",
    "q2",
    "q3",
    "q4",
    "by end of year",
    "within the year",
    "upcoming",
    "soon",
}

# ── INFORMATION signals ──────────────────────────────────────────────────────
_INFO_SUBJECTS = {
    "the system",
    "the tool",
    "the platform",
    "it ",
    "that ",
    "this is",
    "it is",
    "that is",
}


def resolve_clause_intent(text: str, flags: dict = None) -> dict:
    """
    Given a parsed clause text and its linguistic flags, returns:
    {
        "intent": <str>,       # one of the intent constants above
        "reason": <str>,       # human-readable explanation
        "confidence": <float>  # 0.0 – 1.0
    }

    Rules are applied in priority order. First match wins.
    """
    if flags is None:
        flags = {}

    t = text.lower().strip()

    # ── Rule 1: ROADMAP_STATEMENT ────────────────────────────────────────────
    # Pattern: plural/team subject + product noun + time horizon
    # Example: "We will release new features next month."
    has_roadmap_subject = any(
        t.startswith(s) or t.startswith(" " + s) for s in _ROADMAP_SUBJECTS
    )
    has_product_noun = any(n in t for n in _ROADMAP_NOUNS)
    has_time_horizon = any(h in t for h in _ROADMAP_TIME_HORIZON)

    if has_roadmap_subject and has_product_noun and has_time_horizon:
        return {
            "intent": ROADMAP_STATEMENT,
            "reason": (
                "Plural/team subject with product noun and time horizon detected. "
                "Treated as product roadmap announcement, not a personal task."
            ),
            "confidence": 0.90,
        }

    # ── Rule 2: Broad roadmap (subject + product noun, no time, but very generic) ─
    # E.g. "We will ship a new version." — still not an action item
    if has_roadmap_subject and has_product_noun and not has_time_horizon:
        return {
            "intent": ROADMAP_STATEMENT,
            "reason": (
                "Plural/team subject with product noun detected. "
                "No assigned owner or personal commitment present."
            ),
            "confidence": 0.75,
        }

    # ── No match: return UNKNOWN (callers fall through to existing logic) ─────
    return {
        "intent": UNKNOWN,
        "reason": "No deterministic intent pattern matched.",
        "confidence": 0.0,
    }
