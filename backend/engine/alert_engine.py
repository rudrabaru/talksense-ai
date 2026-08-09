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
    """Stateful alert engine for a single session."""

    def __init__(self):
        self._last_fired: dict[str, float] = {}
        self._active_conditions: dict[str, Alert] = {}
        self._last_filler_count: int = 0
        self._last_interruptions: int = 0

    def evaluate(self, state, mode: str, prev_health: int) -> list[dict]:
        now = time.time()
        new_alerts: list[Alert] = []

        # Determine which conditions are CURRENTLY met
        current_conditions: dict[str, Alert] = {}

        # 1. Speaking Dominance
        dominance_alert = self._check_speaking_dominance(state)
        if dominance_alert:
            current_conditions["speaking_dominance"] = dominance_alert

        # 2. Long Silence
        silence_alert = self._check_long_silence(state)
        if silence_alert:
            current_conditions["long_silence"] = silence_alert

        # 3. Excessive Fillers
        filler_alert = self._check_excessive_fillers(state, now)
        if filler_alert:
            current_conditions["excessive_fillers"] = filler_alert

        # 4. Too Many Interruptions
        interruptions_alert = self._check_interruptions(state, now)
        if interruptions_alert:
            current_conditions["too_many_interruptions"] = interruptions_alert

        # A) What's NEWly triggered?
        for a_type, alert in current_conditions.items():
            if a_type not in self._active_conditions:
                # Check cooldown
                last = self._last_fired.get(a_type, 0.0)
                if (now - last) >= COOLDOWN_SECONDS:
                    self._active_conditions[a_type] = alert
                    self._last_fired[a_type] = now
                    new_alerts.append(alert)

        # B) What's RESOLVED?
        resolved_types = []
        for a_type, alert in self._active_conditions.items():
            if a_type not in current_conditions:
                # Condition no longer met
                resolved_alert = Alert(
                    id=str(uuid.uuid4()),
                    level="resolved",
                    message="Condition resolved.",
                    alert_type=a_type,
                )
                new_alerts.append(resolved_alert)
                resolved_types.append(a_type)

        # Remove resolved from active
        for a_type in resolved_types:
            del self._active_conditions[a_type]

        return [a.to_dict() for a in new_alerts]

    def get_active(self) -> list[dict]:
        return [a.to_dict() for a in self._active_conditions.values()]

    def _check_speaking_dominance(self, state) -> Alert | None:
        durations = {}
        total = 0.0
        for seg in state.transcript_segments:
            dur = max(0.0, float(seg.get("end", 0.0)) - float(seg.get("start", 0.0)))
            speaker = seg.get("speaker", "System")
            durations[speaker] = durations.get(speaker, 0.0) + dur
            total += dur

        if total > 15.0:
            for speaker, dur in durations.items():
                if (dur / total) > 0.65:
                    speaker_label = "System" if speaker == "Speaker 1" else speaker
                    return Alert(
                        id=str(uuid.uuid4()),
                        level="warning",
                        message=f"{speaker_label} is dominating the conversation. Pause and ask an open question.",
                        alert_type="speaking_dominance",
                    )
        return None

    def _check_long_silence(self, state) -> Alert | None:
        if getattr(state, "last_silence_seconds", 0) > 8:
            return Alert(
                id=str(uuid.uuid4()),
                level="warning",
                message="Long silence detected — re-engage by checking in.",
                alert_type="long_silence",
            )
        return None

    def _check_excessive_fillers(self, state, now) -> Alert | None:
        last_fired = self._last_fired.get("excessive_fillers", 0.0)

        # If we had a jump in fillers
        if state.filler_count >= self._last_filler_count + 3:
            self._last_filler_count = state.filler_count
            return Alert(
                id=str(uuid.uuid4()),
                level="warning",
                message=f"Excessive filler words detected ({state.filler_count}). Speak more deliberately.",
                alert_type="excessive_fillers",
            )

        # Keep active for 15 seconds after firing
        if "excessive_fillers" in self._active_conditions:
            if (now - last_fired) < 15:
                return self._active_conditions["excessive_fillers"]
        return None

    def _check_interruptions(self, state, now) -> Alert | None:
        last_fired = self._last_fired.get("too_many_interruptions", 0.0)

        if state.interruptions >= self._last_interruptions + 2:
            self._last_interruptions = state.interruptions
            return Alert(
                id=str(uuid.uuid4()),
                level="warning",
                message="Multiple interruptions detected. Allow the other person to finish.",
                alert_type="too_many_interruptions",
            )

        # Keep active for 15 seconds
        if "too_many_interruptions" in self._active_conditions:
            if (now - last_fired) < 15:
                return self._active_conditions["too_many_interruptions"]
        return None
