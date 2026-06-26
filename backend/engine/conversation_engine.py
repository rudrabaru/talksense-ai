"""
TalkSense AI — Conversation Engine

The heart of the product.

Processes each incoming batch of diarized + enriched transcript segments
and updates the live ConversationState for a session.

Every mode (Meeting, Sales, Interview) uses the same engine.
Mode-specific scoring is applied via ScoringProfiles.

Reuses existing analysis logic from services/context_analyzer.py:
  - detect_signals(), compute_meeting_quality_v2()      → Meeting
  - assess_sales_signals(), compute_sales_quality()     → Sales
  - aggregate_sentiment()                               → Both

Called from: ws/audio_handler.py after each transcription batch.
"""

import logging

from engine.alert_engine import AlertEngine
from engine.scoring_profiles import get_profile
from ws.session_manager import ConversationState

logger = logging.getLogger(__name__)

# ── Filler word list ──────────────────────────────────────────────────────────
FILLER_WORDS = {
    "um",
    "uh",
    "er",
    "ah",
    "like",
    "you know",
    "basically",
    "literally",
    "right",
    "so",
    "actually",
    "honestly",
    "kind of",
    "sort of",
}


class ConversationEngine:
    """
    Stateless engine — all state lives in ConversationState.
    One engine instance shared across all sessions.

    Usage:
        engine = get_conversation_engine()
        updated_state, new_alerts = engine.process_segments(segments, state, mode)
    """

    # Per-session AlertEngine instances (keyed by session_id)
    _alert_engines: dict[str, AlertEngine] = {}

    def get_alert_engine(self, session_id: str) -> AlertEngine:
        if session_id not in self._alert_engines:
            self._alert_engines[session_id] = AlertEngine()
        return self._alert_engines[session_id]

    def remove_alert_engine(self, session_id: str) -> None:
        self._alert_engines.pop(session_id, None)

    def process_segments(
        self,
        segments: list,
        state: ConversationState,
        mode: str,
        session_id: str = "default",
        host_embedding: list[float] | None = None,
        speaker_centroids: dict | None = None,
    ) -> tuple[ConversationState, list[dict]]:
        """
        Process new segments and return updated state + new alerts.

        Args:
            segments:   DiarizedSegment list (already enriched with sentiment).
            state:      Current ConversationState (mutated in place).
            mode:       "meeting" | "sales" | "interview".
            session_id: Used to locate the per-session AlertEngine.

        Returns:
            (updated ConversationState, list of new alert dicts)
        """
        if not segments:
            return state, []

        prev_health = state.health_score

        # 1. Update speaking ratios and participation
        self._update_speaking_metrics(segments, state)

        # 2. Update aggregate sentiment
        self._update_sentiment(segments, state)

        # 3. Count filler words
        self._update_fillers(segments, state)

        # 4. Mode-specific analysis
        all_segments = state.transcript_segments  # full session history
        if mode == "sales":
            self._update_sales_metrics(all_segments, state)
        elif mode == "meeting":
            self._update_meeting_metrics(all_segments, state)

        # 5. Compute health score via scoring profile
        state.health_score = self._compute_health(state, mode)

        # 6. Infer Roles (Dynamic Mode Mapping & Host Enrollment)
        self._infer_roles(state, mode, host_embedding, speaker_centroids)

        # 7. Fire alerts
        alert_engine = self.get_alert_engine(session_id)
        new_alerts = alert_engine.evaluate(state, mode, prev_health)

        # Update active alerts on state
        state.active_alerts = alert_engine.get_active()

        return state, new_alerts

    def _infer_roles(
        self,
        state: ConversationState,
        mode: str,
        host_embedding: list[float] | None,
        speaker_centroids: dict | None,
    ) -> None:
        """Infer roles using Voice Enrollment (fallback to First-Speaker) and map to mode."""
        if not state.participation:
            return

        host_speaker_id = None

        # 1. Voice Enrollment Matching
        if host_embedding and speaker_centroids:
            best_match = None
            best_score = -1.0
            
            import numpy as np
            
            host_arr = np.array(host_embedding)
            host_norm = np.linalg.norm(host_arr)
            
            if host_norm > 0:
                for spk, centroid in speaker_centroids.items():
                    cent_arr = np.array(centroid)
                    cent_norm = np.linalg.norm(cent_arr)
                    if cent_norm > 0:
                        score = np.dot(host_arr, cent_arr) / (host_norm * cent_norm)
                        if score > best_score:
                            best_score = score
                            best_match = spk
                            
            if best_match and best_score > 0.65:  # threshold
                host_speaker_id = best_match

        # 2. First-Speaker Fallback (if no enrollment match)
        if not host_speaker_id:
            # Assuming Speaker 1 is the host
            host_speaker_id = "Speaker 1"

        state.host_speaker_id = host_speaker_id

        # 3. Dynamic Mode Mapping
        mode_roles = {
            "sales": {"host": "sales_rep", "guest": "customer"},
            "meeting": {"host": "manager", "guest": "employee"},
            "interview": {"host": "interviewer", "guest": "candidate"},
        }

        mapping = mode_roles.get(mode, {"host": "host", "guest": "guest"})
        
        roles = {}
        for spk in state.participation.keys():
            if spk == host_speaker_id:
                roles[spk] = mapping["host"]
            else:
                roles[spk] = mapping["guest"]
                
        state.roles = roles

    # ── Metric updaters ───────────────────────────────────────────────────────

    @staticmethod
    def _update_speaking_metrics(segments: list, state: ConversationState) -> None:
        """Update speaking_ratio and participation from new segments."""
        for seg in segments:
            speaker = (
                getattr(seg, "speaker", seg.get("speaker", "Speaker 1"))
                if isinstance(seg, dict)
                else seg.speaker
            )
            text = (
                getattr(seg, "text", seg.get("text", ""))
                if isinstance(seg, dict)
                else seg.text
            )
            word_count = len(text.split())
            state.participation[speaker] = (
                state.participation.get(speaker, 0) + word_count
            )

        total_words = sum(state.participation.values()) or 1
        state.speaking_ratio = {
            sp: round((wc / total_words) * 100, 1)
            for sp, wc in state.participation.items()
        }

    @staticmethod
    def _update_sentiment(segments: list, state: ConversationState) -> None:
        """Compute running average sentiment score."""
        scores = []
        for seg in segments:
            val = (
                getattr(seg, "sentiment", None)
                if not isinstance(seg, dict)
                else seg.get("sentiment")
            )
            if val is not None:
                scores.append(val)

        if not scores:
            return

        # Exponential moving average: blend new scores with existing
        new_avg = sum(scores) / len(scores)
        alpha = 0.3  # weight of new data
        blended = alpha * new_avg + (1 - alpha) * state.sentiment_score
        state.sentiment_score = round(blended, 3)

        if blended > 0.1:
            state.sentiment = "positive"
        elif blended < -0.1:
            state.sentiment = "negative"
        else:
            state.sentiment = "neutral"

    @staticmethod
    def _update_fillers(segments: list, state: ConversationState) -> None:
        """Count filler words across new segments."""
        for seg in segments:
            text = (
                getattr(seg, "text", "")
                if not isinstance(seg, dict)
                else seg.get("text", "")
            ).lower()
            for filler in FILLER_WORDS:
                state.filler_count += text.count(filler)

    @staticmethod
    def _update_sales_metrics(all_segments: list, state: ConversationState) -> None:
        """Run sales signal detection on full session transcript."""
        try:
            from services.context_analyzer import (
                OBJECTION_KEYWORDS,
                assess_sales_signals,
            )

            # Convert to the format context_analyzer expects
            seg_dicts = [s if isinstance(s, dict) else s.__dict__ for s in all_segments]

            # Detect objections
            # OBJECTION_KEYWORDS is a dict: {"Pricing": ["price", "cost", ...],
            # "Timeline": [...], ...}
            # Flatten all keyword lists for matching
            objections = []
            for seg in seg_dicts:
                text = seg.get("text", "").lower()
                if isinstance(OBJECTION_KEYWORDS, dict):
                    # Nested dict: {category: [kw1, kw2, ...]}
                    for category, kw_list in OBJECTION_KEYWORDS.items():
                        for kw in (kw_list if isinstance(kw_list, list) else []):
                            if kw in text and text not in [
                                o.get("text", "") for o in objections
                            ]:
                                objections.append(
                                    {
                                        "text": seg.get("text", ""),
                                        "keyword": kw,
                                        "category": category,
                                    }
                                )
                                break
                        else:
                            continue
                        break
                else:
                    # Flat list (fallback)
                    for kw in OBJECTION_KEYWORDS:
                        if kw in text and text not in [
                            o.get("text", "") for o in objections
                        ]:
                            objections.append(
                                {"text": seg.get("text", ""), "keyword": kw}
                            )
                            break
            state.objections = objections

            # Detect buying signals via sales assessment
            signals = assess_sales_signals(seg_dicts, objections, [])
            if signals.get("value_articulated"):
                # Extract the specific text that triggered it
                buying_texts = [
                    s.get("text", "")
                    for s in seg_dicts
                    if any(
                        kw in s.get("text", "").lower()
                        for kw in [
                            "interested",
                            "this looks good",
                            "sounds good",
                            "makes sense",
                        ]
                    )
                ]
                state.buying_signals = buying_texts[-3:]  # keep last 3

        except Exception as exc:
            logger.error(f"ConversationEngine: sales metrics error — {exc}")

    @staticmethod
    def _update_meeting_metrics(all_segments: list, state: ConversationState) -> None:
        """Run meeting signal detection on full session transcript."""
        try:
            from services.context_analyzer import (
                compute_meeting_quality_v2,
                detect_signals,
            )

            seg_dicts = [s if isinstance(s, dict) else s.__dict__ for s in all_segments]

            signals = detect_signals(seg_dicts)
            quality = compute_meeting_quality_v2(signals)

            # Store as a metadata field for report generation
            state.__dict__["meeting_quality"] = quality["label"]
            state.__dict__["meeting_signals"] = signals

        except Exception as exc:
            logger.error(f"ConversationEngine: meeting metrics error — {exc}")

    def _compute_health(self, state: ConversationState, mode: str) -> int:
        """Compute 0–100 health score using the mode's scoring profile."""
        try:
            profile = get_profile(mode)
            normalised = self._normalise_metrics(state, mode)
            return profile.compute_health_score(normalised)
        except Exception as exc:
            logger.error(f"ConversationEngine: health score error — {exc}")
            return state.health_score  # keep last known value

    @staticmethod
    def _normalise_metrics(state: ConversationState, mode: str) -> dict[str, float]:
        """
        Normalise raw metrics to 0–100 for health score computation.
        Each metric is independently scaled to its meaningful range.
        """
        # Participation balance (100 = perfect 50/50, 0 = one person talks 100%)
        ratios = list(state.speaking_ratio.values())
        if len(ratios) >= 2:
            balance = 100 - abs(ratios[0] - ratios[1])
        else:
            balance = 50.0

        # Sentiment (-1 to +1) → 0 to 100
        sentiment_norm = (state.sentiment_score + 1) / 2 * 100

        # Filler penalty (0 fillers = 100, 10+ fillers = 0)
        filler_penalty = max(0.0, 100 - state.filler_count * 10)

        # Objection handling (0 objections = 100, 5+ = 0)
        objection_handling = max(0.0, 100 - len(state.objections) * 20)

        # Buying signals (0 = 50 neutral, each signal adds 10, cap 100)
        buying_signal_score = min(100.0, 50 + len(state.buying_signals) * 10)

        # Participation: average speaker participation normalised
        speaker_count = len(state.participation)
        participation = balance if speaker_count > 1 else 50.0

        # Engagement: proxy from health trend (use sentiment + participation)
        engagement = (sentiment_norm + balance) / 2

        # Listening ratio (inverse of dominant speaker ratio)
        dominant = max(ratios) if ratios else 50.0
        listening_ratio = 100 - dominant  # 100 = perfectly balanced

        return {
            # Meeting profile
            "participation": participation,
            "engagement": engagement,
            "balance": balance,
            "action_items": 50.0,  # Updated when action items are detected
            # Sales profile
            "objection_handling": objection_handling,
            "sentiment": sentiment_norm,
            "listening_ratio": listening_ratio,
            "buying_signals": buying_signal_score,
            # Interview profile (placeholders until Interview mode is built)
            "confidence": sentiment_norm,
            "filler_penalty": filler_penalty,
            "response_quality": 50.0,
            "pause_penalty": 50.0,
        }


# ── Module-level singleton ────────────────────────────────────────────────────
_engine_instance: ConversationEngine | None = None


def get_conversation_engine() -> ConversationEngine:
    """Return the shared ConversationEngine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConversationEngine()
    return _engine_instance
