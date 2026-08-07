"""
TalkSense AI — Alert Engine

Generates real-time, meaningful alerts from conversation metrics.

Rules:
  - 3 severity levels: critical (red), warning (yellow), info (blue)
  - Same alert type: 30-second cooldown before re-firing
  - Maximum 3 active alerts displayed at any time
  - Duplicate messages suppressed

Alert triggers are evaluated after each new set of transcript segments.
New alerts are returned as a list and broadcast to the frontend.
"""

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Alert:
    """A single real-time alert."""

    id: str
    level: str  # "critical" | "warning" | "info"
    message: str
    alert_type: str  # internal key for cooldown tracking
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "alert_type": self.alert_type,
            "timestamp": self.timestamp,
        }


# ── Cooldown & display caps ───────────────────────────────────────────────────
COOLDOWN_SECONDS = 30
MAX_ACTIVE_ALERTS = 3


class AlertEngine:
    """
    Stateful alert engine for a single session.

    Each session gets its own AlertEngine instance (created by ConversationEngine).
    """

    def __init__(self):
        self._last_fired: dict[str, float] = {}  # alert_type → last fire time
        self._active: list[Alert] = []  # currently displayed alerts

    # ── Public interface ──────────────────────────────────────────────────────

    def evaluate(
        self,
        state,  # ConversationState
        mode: str,
        prev_health: int,
    ) -> list[dict]:
        """
        Evaluate all alert conditions and return new alerts to broadcast.

        Args:
            state:       Current ConversationState.
            mode:        "meeting" | "sales" | "interview".
            prev_health: Health score before this update (for trend alerts).

        Returns:
            List of alert dicts ready to broadcast.
        """
        candidates: list[Alert] = []

        # ── Universal alerts ──────────────────────────────────────────────────
        candidates += self._check_sentiment_crash(state, prev_health)
        candidates += self._check_long_silence(state)
        candidates += self._check_engagement_drop(state)

        # ── Mode-specific alerts ──────────────────────────────────────────────
        if mode == "sales":
            candidates += self._check_repeated_objections(state)
            candidates += self._check_buying_signal(state)

        if mode == "meeting":
            candidates += self._check_excessive_fillers(state)

        # ── Apply cooldown & dedup ────────────────────────────────────────────
        new_alerts: list[Alert] = []
        now = time.time()

        for alert in candidates:
            last = self._last_fired.get(alert.alert_type, 0.0)
            if (now - last) < COOLDOWN_SECONDS:
                continue  # still in cooldown

            # Check for duplicate message currently active
            if any(a.message == alert.message for a in self._active):
                continue

            self._last_fired[alert.alert_type] = now
            new_alerts.append(alert)

        # ── Add to active, cap at MAX_ACTIVE_ALERTS ───────────────────────────
        for alert in new_alerts:
            self._active.append(alert)

        # Drop oldest if over cap
        if len(self._active) > MAX_ACTIVE_ALERTS:
            self._active = self._active[-MAX_ACTIVE_ALERTS:]

        return [a.to_dict() for a in new_alerts]

    def get_active(self) -> list[dict]:
        """Return current active alerts."""
        return [a.to_dict() for a in self._active]

    # ── Alert condition checks ────────────────────────────────────────────────

    @staticmethod
    def _check_sentiment_crash(state, prev_health: int) -> list[Alert]:
        drop = prev_health - state.health_score
        if drop >= 25:
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="critical",
                    message="Conversation sentiment has dropped sharply.",
                    alert_type="sentiment_crash",
                )
            ]
        return []



    @staticmethod
    def _check_repeated_objections(state) -> list[Alert]:
        if len(state.objections) >= 3:
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="critical",
                    message=f"Multiple objections detected ({len(state.objections)}). Address concerns directly.",  # noqa: E501
                    alert_type="repeated_objections",
                )
            ]
        return []

    @staticmethod
    def _check_long_silence(state) -> list[Alert]:
        # Silence detected if health < 30 and no recent transcript activity
        # (Proxy: tracked by ConversationEngine pause detector)
        if getattr(state, "last_silence_seconds", 0) > 15:
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="warning",
                    message="Long silence detected — re-engage the conversation.",
                    alert_type="long_silence",
                )
            ]
        return []

    @staticmethod
    def _check_excessive_fillers(state) -> list[Alert]:
        if state.filler_count > 5:
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="warning",
                    message=f"Excessive filler words detected ({state.filler_count}). Speak more deliberately.",  # noqa: E501
                    alert_type="excessive_fillers",
                )
            ]
        return []

    @staticmethod
    def _check_engagement_drop(state) -> list[Alert]:
        if state.health_score < 40:
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="warning",
                    message="Conversation health is low. Engagement may be declining.",
                    alert_type="low_engagement",
                )
            ]
        return []

    @staticmethod
    def _check_buying_signal(state) -> list[Alert]:
        if state.buying_signals:
            latest = state.buying_signals[-1]
            return [
                Alert(
                    id=str(uuid.uuid4()),
                    level="info",
                    message=f'Buying signal detected: "{latest}"',
                    alert_type="buying_signal",
                )
            ]
        return []
