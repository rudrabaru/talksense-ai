import logging
import math
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

WINDOW_SIZE_SECONDS = 30.0
INTERRUPTION_OVERLAP_THRESHOLD = 1.5
INTERRUPTION_WORD_COUNT_THRESHOLD = 3
SILENCE_THRESHOLD = 3.0


def analyze_talk_ratio(segments: List[Any]) -> Dict[str, Any]:
    """
    Computes Talk Ratio Timeline and Conversation Flow metrics
    strictly from transcript timestamps and speaker attribution.

    Args:
        segments: List of TranscriptSegment models ordered by start_time.

    Returns:
        A dictionary containing:
            - summary: Global conversational flow stats
            - overall_participation: Total participation % per speaker
            - timeline: List of 30-second bucket metrics
    """
    if not segments:
        return {
            "summary": {
                "total_duration_seconds": 0.0,
                "longest_monologue_seconds": 0.0,
                "longest_monologue_speaker": None,
                "average_turn_length_seconds": 0.0,
                "speaker_switch_count": 0,
                "interruption_count": 0,
                "silence_duration_seconds": 0.0,
            },
            "overall_participation": {},
            "timeline": [],
        }

    # Track overall summary metrics
    speaker_talk_time: Dict[str, float] = {}
    longest_monologue_seconds = 0.0
    longest_monologue_speaker = None
    speaker_switch_count = 0
    interruption_count = 0
    silence_duration_seconds = 0.0

    # State tracking for monologues and turns
    current_speaker = None
    current_monologue_start = 0.0
    current_monologue_end = 0.0
    turn_count = 0
    total_talk_time = 0.0

    # 1. First pass: Analyze overall flow (switches, interruptions, silences,
    # monologues)
    for i, seg in enumerate(segments):
        speaker = seg.speaker_id or "Unknown"
        start = seg.start_time
        end = seg.end_time
        duration = max(0.0, end - start)
        text = seg.text or ""
        word_count = len(text.split())

        # Accumulate total talk time globally
        speaker_talk_time[speaker] = speaker_talk_time.get(speaker, 0.0) + duration
        total_talk_time += duration

        if current_speaker is None:
            current_speaker = speaker
            current_monologue_start = start
            current_monologue_end = end
            turn_count += 1
        else:
            if speaker != current_speaker:
                speaker_switch_count += 1
                turn_count += 1

                # Check for monologue record before switching
                monologue_dur = current_monologue_end - current_monologue_start
                if monologue_dur > longest_monologue_seconds:
                    longest_monologue_seconds = monologue_dur
                    longest_monologue_speaker = current_speaker

                # New speaker starts monologue
                current_speaker = speaker
                current_monologue_start = start
                current_monologue_end = end

                # Check for interruption
                prev_seg = segments[i - 1]
                overlap = prev_seg.end_time - start
                if overlap > 0:
                    if (
                        overlap > INTERRUPTION_OVERLAP_THRESHOLD
                        or word_count > INTERRUPTION_WORD_COUNT_THRESHOLD
                    ):
                        interruption_count += 1
            else:
                # Same speaker continuing
                current_monologue_end = max(current_monologue_end, end)

        # Check for silence gap
        if i > 0:
            prev_seg = segments[i - 1]
            gap = start - prev_seg.end_time
            if gap > SILENCE_THRESHOLD:
                silence_duration_seconds += gap

    # Final monologue check
    if current_speaker is not None:
        monologue_dur = current_monologue_end - current_monologue_start
        if monologue_dur > longest_monologue_seconds:
            longest_monologue_seconds = monologue_dur
            longest_monologue_speaker = current_speaker

    # Total conversation duration based on max end_time
    total_duration_seconds = max(s.end_time for s in segments)
    average_turn_length_seconds = (
        total_talk_time / turn_count if turn_count > 0 else 0.0
    )

    # Overall participation
    overall_participation = {}
    if total_talk_time > 0:
        for spk, duration in speaker_talk_time.items():
            overall_participation[spk] = round((duration / total_talk_time) * 100, 1)

    # Calculate dominance globally
    max_participation = 0.0
    if overall_participation:
        max_participation = max(overall_participation.values())

    conversation_balance = "GOOD"
    if max_participation > 75.0:
        conversation_balance = "POOR"
    elif max_participation >= 60.0:
        conversation_balance = "WARNING"

    monologue_risk = "LOW"
    if longest_monologue_seconds > 90.0:
        monologue_risk = "HIGH"
    elif longest_monologue_seconds >= 45.0:
        monologue_risk = "MEDIUM"

    # 2. Second pass: Bucket into 30-second windows
    num_buckets = math.ceil(total_duration_seconds / WINDOW_SIZE_SECONDS)
    buckets = []

    for b in range(num_buckets):
        window_start = b * WINDOW_SIZE_SECONDS
        window_end = window_start + WINDOW_SIZE_SECONDS

        bucket_talk_time: Dict[str, float] = {}
        bucket_total = 0.0

        for seg in segments:
            # Overlap between segment and bucket
            overlap_start = max(seg.start_time, window_start)
            overlap_end = min(seg.end_time, window_end)
            overlap_duration = overlap_end - overlap_start

            if overlap_duration > 0:
                spk = seg.speaker_id or "Unknown"
                bucket_talk_time[spk] = (
                    bucket_talk_time.get(spk, 0.0) + overlap_duration
                )
                bucket_total += overlap_duration

        # Format bucket metrics
        bucket_speakers = {}
        for spk, duration in bucket_talk_time.items():
            part = (
                round((duration / bucket_total) * 100, 1) if bucket_total > 0 else 0.0
            )
            bucket_speakers[spk] = {
                "talk_time": round(duration, 1),
                "participation": part,
                "dominance": part,  # In a window, dominance is essentially participation  # noqa: E501
            }

        buckets.append(
            {
                "window_start": window_start,
                "window_end": window_end,
                "speakers": bucket_speakers,
            }
        )

    return {
        "summary": {
            "total_duration_seconds": round(total_duration_seconds, 1),
            "longest_monologue_seconds": round(longest_monologue_seconds, 1),
            "longest_monologue_speaker": longest_monologue_speaker,
            "average_turn_length_seconds": round(average_turn_length_seconds, 1),
            "speaker_switch_count": speaker_switch_count,
            "interruption_count": interruption_count,
            "silence_duration_seconds": round(silence_duration_seconds, 1),
            "dominance_percent": round(max_participation, 1),
            "monologue_risk": monologue_risk,
            "conversation_balance": conversation_balance,
        },
        "overall_participation": overall_participation,
        "timeline": buckets,
    }
