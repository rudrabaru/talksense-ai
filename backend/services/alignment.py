import logging

logger = logging.getLogger(__name__)


class WordAligner:
    """
    Aligns Whisper word-level timestamps with Pyannote speaker intervals
    using a maximum-overlap strategy.
    """

    @staticmethod
    def align_words(
        whisper_segments: list, speaker_intervals: list[dict]
    ) -> list[dict]:
        """
        Aligns raw Whisper segments with Pyannote speaker intervals at the word level.

        Args:
            whisper_segments: List of dicts from DB [{"start": float, "end": float, "text": str}]
            speaker_intervals: List of dicts [{"start": float, "end": float, "speaker": str}]

        Returns:
            List of dicts representing aligned words:
            [{"start": float, "end": float, "text": str, "speaker": str}]
        """
        # Flatten words from segments
        all_words = []
        for seg in whisper_segments:
            words = (
                getattr(seg, "words", [])
                if not isinstance(seg, dict)
                else seg.get("words", [])
            )
            if not words:
                # Fallback to basic word splitting if DB doesn't have word-level timestamps
                text = (
                    getattr(seg, "text", "")
                    if not isinstance(seg, dict)
                    else seg.get("text", "")
                )
                seg_start = (
                    getattr(seg, "start_time", 0.0)
                    if not isinstance(seg, dict)
                    else seg.get("start_time", 0.0)
                )
                seg_end = (
                    getattr(seg, "end_time", 0.0)
                    if not isinstance(seg, dict)
                    else seg.get("end_time", 0.0)
                )

                tokens = text.split()
                if not tokens:
                    continue

                duration = seg_end - seg_start
                word_duration = duration / len(tokens)

                for i, token in enumerate(tokens):
                    w_start = seg_start + (i * word_duration)
                    w_end = w_start + word_duration
                    word_str = " " + token if i > 0 else token
                    all_words.append(
                        {
                            "word": word_str,
                            "start": float(w_start),
                            "end": float(w_end),
                            "probability": 1.0,
                            "speaker": "Unknown",
                        }
                    )
            else:
                for w in words:
                    word_text = (
                        getattr(w, "word", "")
                        if not isinstance(w, dict)
                        else w.get("word", "")
                    )
                    w_start = (
                        getattr(w, "start", 0.0)
                        if not isinstance(w, dict)
                        else w.get("start", 0.0)
                    )
                    w_end = (
                        getattr(w, "end", 0.0)
                        if not isinstance(w, dict)
                        else w.get("end", 0.0)
                    )
                    w_prob = (
                        getattr(w, "probability", 0.0)
                        if not isinstance(w, dict)
                        else w.get("probability", 0.0)
                    )

                    if word_text.strip():
                        all_words.append(
                            {
                                "word": word_text,
                                "start": float(w_start),
                                "end": float(w_end),
                                "probability": float(w_prob),
                                "speaker": "Unknown",
                            }
                        )

        if not all_words:
            return []

        # Sort Pyannote intervals just in case
        intervals = sorted(speaker_intervals, key=lambda x: x["start"])

        aligned_words = []
        for w in all_words:
            w_start = w["start"]
            w_end = w["end"]

            max_overlap = 0.0
            best_speaker = "Unknown"

            for interval in intervals:
                i_start = interval["start"]
                i_end = interval["end"]

                # If interval is strictly after word, stop checking (since sorted)
                if i_start > w_end:
                    break

                # If word is strictly after interval, skip
                if w_start >= i_end:
                    continue

                # Calculate overlap
                overlap_start = max(w_start, i_start)
                overlap_end = min(w_end, i_end)
                overlap_duration = overlap_end - overlap_start

                if overlap_duration > max_overlap:
                    max_overlap = overlap_duration
                    best_speaker = interval["speaker"]

            # If no intersection but close to a boundary (within 1 second gap)
            if best_speaker == "Unknown":
                # Find nearest interval
                nearest_speaker = "Unknown"
                min_dist = 1.0  # Max 1.0s gap
                for interval in intervals:
                    dist = min(
                        abs(w_start - interval["end"]), abs(w_end - interval["start"])
                    )
                    if w_start >= interval["start"] and w_end <= interval["end"]:
                        dist = 0  # Inside (already caught above, but safe)

                    if dist < min_dist:
                        min_dist = dist
                        nearest_speaker = interval["speaker"]

                best_speaker = nearest_speaker

            w["speaker"] = best_speaker
            aligned_words.append(w)

        return aligned_words


class SpeakerCleanup:
    """
    Deterministic rules engine to clean up speaker assignments and group words into segments.
    """

    @staticmethod
    def process(aligned_words: list[dict]) -> list[dict]:
        """
        Applies island-smoothing and builds grouped transcript segments.

        Args:
            aligned_words: Flat list of word dicts with "speaker" keys.

        Returns:
            List of segmented transcript chunks ready for DB/Frontend:
            [{"speaker": "Speaker 0", "text": "Hello world", "start": 0.5, "end": 2.0}]
        """
        if not aligned_words:
            return []

        # 1. Island Smoothing (Filter isolated words)
        # Rule: If a speaker turn is exactly 1 word and < 500ms, sandwiched between the same speaker,
        # rewrite its speaker to match the sandwich bread.
        for i in range(1, len(aligned_words) - 1):
            prev_spk = aligned_words[i - 1]["speaker"]
            next_spk = aligned_words[i + 1]["speaker"]
            curr_spk = aligned_words[i]["speaker"]

            if curr_spk != prev_spk and prev_spk == next_spk:
                duration = aligned_words[i]["end"] - aligned_words[i]["start"]
                if duration < 0.5:
                    aligned_words[i]["speaker"] = prev_spk

        # 2. Group into segments
        segments = []
        current_segment = None

        for w in aligned_words:
            spk = w["speaker"]
            if current_segment is None:
                current_segment = {
                    "speaker": spk,
                    "start": w["start"],
                    "end": w["end"],
                    "words": [w],
                }
            elif current_segment["speaker"] == spk:
                # Same speaker, extend segment
                current_segment["end"] = w["end"]
                current_segment["words"].append(w)
            else:
                # Speaker switch
                # Build text
                current_segment["text"] = "".join(
                    x["word"] for x in current_segment["words"]
                ).strip()
                segments.append(current_segment)
                current_segment = {
                    "speaker": spk,
                    "start": w["start"],
                    "end": w["end"],
                    "words": [w],
                }

        if current_segment:
            current_segment["text"] = "".join(
                x["word"] for x in current_segment["words"]
            ).strip()
            segments.append(current_segment)

        # 3. Gap Bridging
        # If two consecutive segments by the same speaker have a gap < 1.0s, merge them
        merged_segments = []
        for seg in segments:
            if not merged_segments:
                merged_segments.append(seg)
            else:
                last_seg = merged_segments[-1]
                if last_seg["speaker"] == seg["speaker"]:
                    gap = seg["start"] - last_seg["end"]
                    if gap < 1.0:
                        # Merge
                        last_seg["end"] = seg["end"]
                        last_seg["text"] = last_seg["text"] + " " + seg["text"]
                        last_seg["words"].extend(seg["words"])
                    else:
                        merged_segments.append(seg)
                else:
                    merged_segments.append(seg)

        return merged_segments
