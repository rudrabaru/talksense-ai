"""
TalkSense AI — Word Speaker Aligner

Aligns a stream of Whisper words with Pyannote speaker segments using temporal overlap.
Used by both the live pipeline (diarizer.py) and the offline pipeline (post_session_diarizer.py).
"""


def align_words_to_speakers(
    words: list[dict],
    speaker_segments: list[tuple[float, float, str]],
    fallback_speaker: str = "Speaker 1",
) -> list[dict]:
    """
    Assigns the most appropriate speaker to each word based on temporal overlap.

    Args:
        words: List of dictionaries with keys: 'word', 'start', 'end', 'probability' (or 'confidence')
        speaker_segments: List of tuples (start_sec, end_sec, speaker_label)
        fallback_speaker: Speaker to assign if no segment is found

    Returns:
        List of dictionaries with the same keys + 'speaker'
    """
    if not words:
        return []

    if not speaker_segments:
        return [
            {
                "word": w.get("word", ""),
                "start": w.get("start", 0.0),
                "end": w.get("end", 0.0),
                "speaker": fallback_speaker,
                "confidence": w.get("probability", w.get("confidence", 0.0)),
            }
            for w in words
        ]

    aligned_words = []

    for w in words:
        w_start = w.get("start", 0.0)
        w_end = w.get("end", 0.0)
        w_word = w.get("word", "")
        w_conf = w.get("probability", w.get("confidence", 0.0))

        best_speaker = fallback_speaker
        max_overlap = -1.0
        nearest_distance = float("inf")
        nearest_speaker = fallback_speaker

        for seg_start, seg_end, speaker in speaker_segments:
            # Calculate overlap
            overlap_start = max(w_start, seg_start)
            overlap_end = min(w_end, seg_end)
            overlap = overlap_end - overlap_start

            if overlap > 0 and overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker

            # Keep track of nearest segment for fallback if no overlap
            if overlap <= 0:
                dist = min(abs(w_start - seg_end), abs(seg_start - w_end))
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_speaker = speaker

        if max_overlap > 0:
            assigned_speaker = best_speaker
        else:
            assigned_speaker = nearest_speaker

        aligned_words.append(
            {
                "word": w_word,
                "start": w_start,
                "end": w_end,
                "speaker": assigned_speaker,
                "confidence": w_conf,
            }
        )

    # 5-Word Smoothing was removed in Sprint 13.8 because it actively destroyed
    # legitimate short turns (1-2 word backchannels like "yes", "exactly").
    # We rely purely on word-level alignment and downstream post-processing.

    return aligned_words
