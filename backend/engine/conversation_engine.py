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

    The engine reads from state.transcript_segments[] using internal
    watermarks to compute the delta of genuinely new text.

    Usage:
        engine = get_conversation_engine()
        updated_state, new_alerts = engine.process_segments(state, mode)
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
        state: ConversationState,
        mode: str,
        session_id: str = "default",
        host_embedding: list[float] | None = None,
        speaker_centroids: dict | None = None,
    ) -> tuple[ConversationState, list[dict]]:
        """
        Process new transcript data and return updated state + new alerts.

        The engine reads directly from state.transcript_segments[] using its
        own watermarks.  It computes the delta (new segments + boundary growth
        from overlap merges) and passes only genuinely new text to the metric
        updaters.

        Args:
            state:      Current ConversationState (mutated in place).
            mode:       "meeting" | "sales" | "interview".
            session_id: Used to locate the per-session AlertEngine.

        Returns:
            (updated ConversationState, list of new alert dicts)
        """
        all_segments = state.transcript_segments
        new_start = state._engine_processed_index

        # ── Derive the delta: boundary growth + genuinely new segments ────────
        segments_to_process: list[dict] = []

        # 1. Boundary check: did the last-processed segment grow via merge?
        if new_start > 0 and new_start <= len(all_segments):
            boundary_seg = all_segments[new_start - 1]
            boundary_text = (
                boundary_seg.get("text", "")
                if isinstance(boundary_seg, dict)
                else getattr(boundary_seg, "text", "")
            )
            boundary_words = boundary_text.split()
            prev_word_count = state._boundary_word_count

            if len(boundary_words) > prev_word_count:
                # The overlap merge extended this segment — extract only new words
                delta_words = boundary_words[prev_word_count:]
                speaker = (
                    boundary_seg.get("speaker", "Speaker 1")
                    if isinstance(boundary_seg, dict)
                    else getattr(boundary_seg, "speaker", "Speaker 1")
                )
                segments_to_process.append(
                    {
                        "text": " ".join(delta_words),
                        "speaker": speaker,
                        "start": (
                            boundary_seg.get("start", 0.0)
                            if isinstance(boundary_seg, dict)
                            else getattr(boundary_seg, "start", 0.0)
                        ),
                        "end": (
                            boundary_seg.get("end", 0.0)
                            if isinstance(boundary_seg, dict)
                            else getattr(boundary_seg, "end", 0.0)
                        ),
                        "sentiment": (
                            boundary_seg.get("sentiment", 0.0)
                            if isinstance(boundary_seg, dict)
                            else getattr(boundary_seg, "sentiment", 0.0)
                        ),
                    }
                )

        # 2. Add genuinely new segments (everything after the watermark)
        for seg in all_segments[new_start:]:
            segments_to_process.append(seg if isinstance(seg, dict) else seg.__dict__)

        # 3. Advance watermarks BEFORE processing (safe: we hold the session lock)
        state._engine_processed_index = len(all_segments)
        if all_segments:
            last_seg = all_segments[-1]
            last_text = (
                last_seg.get("text", "")
                if isinstance(last_seg, dict)
                else getattr(last_seg, "text", "")
            )
            state._boundary_word_count = len(last_text.split())
        else:
            state._boundary_word_count = 0

        if not segments_to_process:
            return state, []

        prev_health = state.health_score

        # 1. Update speaking ratios and participation
        self._update_speaking_metrics(segments_to_process, state)

        # 2. Update aggregate sentiment
        self._update_sentiment(segments_to_process, state)

        # 3. Count filler words (incremental — processes only new segments)
        self._update_fillers(segments_to_process, state)

        # 4. Mode-specific analysis (incremental — processes only new segments)
        if mode == "sales":
            self._update_sales_metrics(segments_to_process, state)
        elif mode == "meeting":
            self._update_meeting_metrics(segments_to_process, state)

        # 5. Compute health score via scoring profile
        state.health_score = self._compute_health(state, mode)

        # 6. Infer Roles (Dynamic Mode Mapping & Host Enrollment)
        self._infer_roles(state, mode, host_embedding, speaker_centroids)

        # 7. Fire alerts
        alert_engine = self.get_alert_engine(session_id)
        new_alerts = alert_engine.evaluate(state, mode, prev_health)

        # Update active alerts on state
        state.active_alerts = alert_engine.get_active()

        # 8. Generate Coaching Recommendations
        self._generate_coaching_recommendations(state, mode)

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

    def _generate_coaching_recommendations(
        self, state: ConversationState, mode: str
    ) -> None:
        """Deterministically generate real-time coaching recommendations from ConversationState."""
        tips = []

        # 1. Speaking Balance
        if state.speaking_ratio:
            dominant_speaker = max(
                state.speaking_ratio, key=lambda k: state.speaking_ratio[k]
            )
            if state.speaking_ratio[dominant_speaker] > 70:
                is_host = state.host_speaker_id == dominant_speaker
                if is_host or not state.host_speaker_id:
                    tips.append(
                        {
                            "id": "coach_speaking_balance",
                            "severity": "medium",
                            "title": "Speaking Balance",
                            "recommendation": "Pause and ask an open question.",
                            "reason": f"You are speaking {state.speaking_ratio[dominant_speaker]:.0f}% of the time.",
                        }
                    )

        # 2. Filler Density
        duration_minutes = max(1.0, getattr(state, "duration_seconds", 0.0) / 60.0)
        filler_density = state.filler_count / duration_minutes
        if filler_density > 3:
            tips.append(
                {
                    "id": "coach_filler_density",
                    "severity": "low",
                    "title": "Filler Word Density",
                    "recommendation": "Slow down and speak more deliberately.",
                    "reason": f"High filler word count detected ({int(filler_density)}/min).",
                }
            )

        # 3. Interruptions
        if state.interruptions > 3:
            tips.append(
                {
                    "id": "coach_interruptions",
                    "severity": "medium",
                    "title": "Interruptions",
                    "recommendation": "Let the speaker finish their thought.",
                    "reason": f"High interruption frequency ({state.interruptions} detected).",
                }
            )

        # 4. Objections (Sales mode)
        if mode == "sales" and state.objection_timeline:
            last_obj = state.objection_timeline[-1]
            if state.duration_seconds - last_obj.get("timestamp", 0) < 120:
                tips.append(
                    {
                        "id": "coach_objection",
                        "severity": "high",
                        "title": f"Objection: {last_obj.get('category', 'Concern').title()}",
                        "recommendation": "Address concern directly using FEEL-FELT-FOUND.",
                        "reason": f"Client mentioned: '{last_obj.get('keyword', '')}'.",
                    }
                )

        # 5. Buying Signals (Sales mode)
        if mode == "sales" and state.buying_signal_timeline:
            last_buy = state.buying_signal_timeline[-1]
            if state.duration_seconds - last_buy.get("timestamp", 0) < 120:
                tips.append(
                    {
                        "id": "coach_buying_signal",
                        "severity": "high",
                        "title": "Buying Signal Detected",
                        "recommendation": "Shift toward closing or next steps.",
                        "reason": "Client expressed positive intent.",
                    }
                )

        # Sort by severity (high -> medium -> low)
        severity_order = {"high": 0, "medium": 1, "low": 2}
        tips.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

        state.coaching_tips = tips

    # ── Metric updaters ───────────────────────────────────────────────────────

    @staticmethod
    def _update_speaking_metrics(segments: list, state: ConversationState) -> None:
        """Update speaking_ratio, participation, interruptions, and speaker_switches."""
        INTERRUPTION_OVERLAP_THRESHOLD = 1.5
        INTERRUPTION_WORD_COUNT_THRESHOLD = 3

        last_speaker = None
        last_end_time = 0.0
        if state.transcript_segments:
            last_seg = state.transcript_segments[-1]
            last_speaker = getattr(
                last_seg,
                "speaker",
                last_seg.get("speaker") if isinstance(last_seg, dict) else None,
            )
            # Try to get end_time/end, defaulting to 0.0 if not found or None
            last_end_val = (
                last_seg.get("end_time", last_seg.get("end", 0.0))
                if isinstance(last_seg, dict)
                else getattr(last_seg, "end_time", getattr(last_seg, "end", 0.0))
            )
            last_end_time = float(last_end_val if last_end_val is not None else 0.0)

        for seg in segments:
            speaker = (
                getattr(seg, "speaker", seg.get("speaker", "Speaker 1"))
                if isinstance(seg, dict)
                else getattr(seg, "speaker", "Speaker 1")
            )
            text = (
                getattr(seg, "text", seg.get("text", ""))
                if isinstance(seg, dict)
                else getattr(seg, "text", "")
            )
            if text is None:
                text = ""

            word_count = len(text.split())

            # Try to get start_time/start, defaulting to 0.0 if not found or None
            start_val = (
                seg.get("start_time", seg.get("start", 0.0))
                if isinstance(seg, dict)
                else getattr(seg, "start_time", getattr(seg, "start", 0.0))
            )
            start_time = float(start_val if start_val is not None else 0.0)
            state.participation[speaker] = (
                state.participation.get(speaker, 0) + word_count
            )

            # Flow tracking
            if last_speaker is not None and speaker != last_speaker:
                state.speaker_switches += 1
                overlap = last_end_time - start_time
                if (
                    overlap > INTERRUPTION_OVERLAP_THRESHOLD
                    or word_count > INTERRUPTION_WORD_COUNT_THRESHOLD
                ):
                    state.interruptions += 1

            last_speaker = speaker
            # Try to get end_time/end, defaulting to 0.0 if not found or None
            end_val = (
                seg.get("end_time", seg.get("end", 0.0))
                if isinstance(seg, dict)
                else getattr(seg, "end_time", getattr(seg, "end", 0.0))
            )
            last_end_time = float(end_val if end_val is not None else 0.0)

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
        """Count filler words across new segments (incremental O(1))."""
        import re

        for seg in segments:
            text = (
                getattr(seg, "text", "")
                if not isinstance(seg, dict)
                else seg.get("text", "")
            ).lower()

            # Use regex to find exact word boundaries for filler words
            for filler in FILLER_WORDS:
                pattern = r"\b" + re.escape(filler) + r"\b"
                state.filler_count += len(re.findall(pattern, text))

        # Advance watermark (safety guard for index-based callers)
        state.fillers_processed_index = len(state.transcript_segments)

    @staticmethod
    def _update_sales_metrics(new_segments: list, state: ConversationState) -> None:
        """Incrementally detect sales signals from NEW segments only (O(1))."""
        if not new_segments:
            return
        try:
            from services.context_analyzer import (
                BUYING_SIGNAL_KEYWORDS,
                OBJECTION_KEYWORDS,
                assess_sales_signals,
            )
            from services.conversation_state_resolver import resolve_conversation_state
            from services.linguistic_parser import annotate_segments

            # Convert only NEW segments to dicts
            seg_dicts = [s if isinstance(s, dict) else s.__dict__ for s in new_segments]
            annotate_segments(seg_dicts)
            resolve_conversation_state(seg_dicts)

            # Build set of already-known objection texts for dedup
            known_texts = {o.get("text", "") for o in state.objections}

            # Detect objections in NEW segments only, append to existing
            for seg in seg_dicts:
                start_time = seg.get("start_time", 0.0)
                for clause in seg.get("clauses", []):
                    if clause.get("is_conditional") or clause.get("is_abandoned"):
                        continue
                    text = clause.get("text", "").lower()
                    if isinstance(OBJECTION_KEYWORDS, dict):
                        for category, kw_list in OBJECTION_KEYWORDS.items():
                            for kw in kw_list if isinstance(kw_list, list) else []:
                                if kw in text and text not in known_texts:
                                    obj = {
                                        "text": clause.get("text", ""),
                                        "keyword": kw,
                                        "category": category,
                                        "timestamp": start_time,
                                    }
                                    state.objections.append(obj)
                                    state.objection_timeline.append(obj)
                                    known_texts.add(text)
                                    break
                            else:
                                continue
                            break
                    else:
                        for kw in OBJECTION_KEYWORDS:
                            if kw in text and text not in known_texts:
                                obj = {
                                    "text": clause.get("text", ""),
                                    "keyword": kw,
                                    "timestamp": start_time,
                                }
                                state.objections.append(obj)
                                state.objection_timeline.append(obj)
                                known_texts.add(text)
                                break

            # Detect buying signals in NEW segments only
            signals = assess_sales_signals(seg_dicts, state.objections, [])
            if signals.get("value_articulated"):
                for s in seg_dicts:
                    start_time = s.get("start_time", 0.0)
                    for c in s.get("clauses", []):
                        if (
                            not c.get("is_negated")
                            and not c.get("is_conditional")
                            and not c.get("is_abandoned")
                        ):
                            if any(
                                kw in c.get("text", "").lower()
                                for kw in BUYING_SIGNAL_KEYWORDS
                            ):
                                state.buying_signal_timeline.append(
                                    {"text": c.get("text", ""), "timestamp": start_time}
                                )
                # Keep last 3 buying signal strings
                state.buying_signals = [
                    b["text"] for b in state.buying_signal_timeline[-3:]
                ]

            # Advance watermark
            state.sales_metrics_processed_index = len(state.transcript_segments)

        except Exception:
            pass

    @staticmethod
    def _update_meeting_metrics(new_segments: list, state: ConversationState) -> None:
        """Incrementally detect meeting signals from NEW segments only (O(1))."""
        if not new_segments:
            return
        try:
            from services.context_analyzer import (
                compute_meeting_quality_v2,
                detect_decisions,
                detect_signals,
                extract_actions,
            )
            from services.conversation_state_resolver import resolve_conversation_state
            from services.linguistic_parser import annotate_segments

            # Convert only NEW segments to dicts
            seg_dicts = [s if isinstance(s, dict) else s.__dict__ for s in new_segments]
            annotate_segments(seg_dicts)
            resolve_conversation_state(seg_dicts)

            # Detect signals in new segments, merge with cached signals via boolean OR
            new_signals = detect_signals(seg_dicts)
            cached = state._meeting_signals_cache
            merged = {}
            for key in set(list(new_signals.keys()) + list(cached.keys())):
                merged[key] = bool(new_signals.get(key)) or bool(cached.get(key))
            state._meeting_signals_cache = merged

            quality = compute_meeting_quality_v2(merged)

            # Store as a metadata field for report generation
            state.__dict__["meeting_quality"] = quality["label"]
            state.__dict__["meeting_signals"] = merged

            # Append new action items and decisions (incremental)
            new_actions = extract_actions(seg_dicts)
            new_decisions = detect_decisions(seg_dicts)

            # Dedup by task text before appending
            existing_tasks = {a.get("task", "") for a in state.action_items}
            for a in new_actions:
                if a.get("task", "") not in existing_tasks:
                    state.action_items.append(a)
                    existing_tasks.add(a.get("task", ""))

            existing_decisions = {d.get("text", "") for d in state.decisions}
            for d in new_decisions:
                if d.get("text", "") not in existing_decisions:
                    state.decisions.append(d)
                    existing_decisions.add(d.get("text", ""))

            # Advance watermark
            state.meeting_metrics_processed_index = len(state.transcript_segments)

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

        # Filler penalty via density (fillers per minute)
        duration_minutes = max(1.0, getattr(state, "duration_seconds", 0.0) / 60.0)
        filler_density = state.filler_count / duration_minutes
        # 0 fillers/min = 100, 5+ fillers/min = 0 (20 penalty per filler/min)
        filler_penalty = max(0.0, 100 - filler_density * 20)

        # Pause penalty (based on silence > 10 seconds)
        silence = getattr(state, "last_silence_seconds", 0.0)
        pause_penalty = max(0.0, 100.0 - max(0.0, silence - 10) * 10)

        # Action items (0 = 50, each adds 10, cap 100)
        action_items_score = min(100.0, 50.0 + len(state.action_items) * 10)

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
            "action_items": action_items_score,
            # Sales profile
            "objection_handling": objection_handling,
            "sentiment": sentiment_norm,
            "listening_ratio": listening_ratio,
            "buying_signals": buying_signal_score,
            # Interview profile
            "confidence": sentiment_norm,
            "filler_penalty": filler_penalty,
            "response_quality": 50.0,  # Placeholder
            "pause_penalty": pause_penalty,
        }


# ── Module-level singleton ────────────────────────────────────────────────────
_engine_instance: ConversationEngine | None = None


def get_conversation_engine() -> ConversationEngine:
    """Return the shared ConversationEngine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ConversationEngine()
    return _engine_instance
