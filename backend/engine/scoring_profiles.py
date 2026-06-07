"""
TalkSense AI — Scoring Profiles

Defines the weighting configuration for each conversation mode.
Weights are loaded from this file (not hardcoded in logic) so they
can be tuned without changing engine code.

Health Score formula (0–100):
  health_score = Σ (metric_value * weight) for each metric in profile

Each metric_value is normalised to 0–100 before weighting.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringProfile:
    """
    Weight configuration for a conversation mode.

    All weights must sum to 1.0.
    Keys map to metric names in ConversationState.
    """
    mode: str
    weights: dict[str, float]

    def compute_health_score(self, normalised_metrics: dict[str, float]) -> int:
        """
        Compute weighted health score from normalised metrics.

        Args:
            normalised_metrics: Dict of metric_name → 0.0–100.0

        Returns:
            Integer health score 0–100.
        """
        score = 0.0
        for metric, weight in self.weights.items():
            value = normalised_metrics.get(metric, 50.0)  # default 50 if missing
            score += value * weight
        return max(0, min(100, round(score)))


# ── Mode Profiles ─────────────────────────────────────────────────────────────

MEETING_PROFILE = ScoringProfile(
    mode="meeting",
    weights={
        "participation":  0.40,
        "engagement":     0.30,
        "balance":        0.20,
        "action_items":   0.10,
    },
)

SALES_PROFILE = ScoringProfile(
    mode="sales",
    weights={
        "objection_handling": 0.35,
        "sentiment":          0.25,
        "listening_ratio":    0.20,
        "buying_signals":     0.20,
    },
)

INTERVIEW_PROFILE = ScoringProfile(
    mode="interview",
    weights={
        "confidence":       0.35,
        "filler_penalty":   0.25,
        "response_quality": 0.25,
        "pause_penalty":    0.15,
    },
)

_PROFILES: dict[str, ScoringProfile] = {
    "meeting":   MEETING_PROFILE,
    "sales":     SALES_PROFILE,
    "interview": INTERVIEW_PROFILE,
}


def get_profile(mode: str) -> ScoringProfile:
    """
    Return the scoring profile for a given mode.

    Raises:
        ValueError if mode is not recognised.
    """
    profile = _PROFILES.get(mode)
    if profile is None:
        raise ValueError(f"Unknown mode {mode!r}. Valid: {list(_PROFILES)}")
    return profile
