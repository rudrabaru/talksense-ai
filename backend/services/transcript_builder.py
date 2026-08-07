import logging

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a string.
    A common rough estimate is 4 characters per token.
    """
    return len(text) // 4


def build_transcript_string(segments: list[dict], max_tokens: int = 50000) -> str:
    """
    Converts a list of transcript segment dictionaries into a chronological
    string suitable for LLM context, respecting token limits.
    
    Segments should have:
    - start_time (float): seconds
    - text (str): transcript text
    """
    if not segments:
        return ""

    # Sort segments chronologically
    sorted_segments = sorted(segments, key=lambda x: x.get("start_time", 0.0))

    formatted_lines = []
    for seg in sorted_segments:
        start = seg.get("start_time", 0.0)
        text = seg.get("text", "").strip()
        segment_id = seg.get("segment_id", "NO_ID")
        if not text:
            continue
            
        # Format: [MM:SS] [ID] System: text
        mins = int(start // 60)
        secs = int(start % 60)
        line = f"[{mins:02d}:{secs:02d}] [{segment_id}] System: {text}"
        formatted_lines.append(line)

    full_transcript = "\n".join(formatted_lines)
    estimated_tokens = _estimate_tokens(full_transcript)
    
    logger.info(f"Transcript builder generated {len(formatted_lines)} lines, estimated {estimated_tokens} tokens.")

    if estimated_tokens <= max_tokens:
        return full_transcript

    # Truncation logic: Preserve beginning (20%) and ending (80%)
    logger.info(f"Transcript exceeds max_tokens ({max_tokens}). Truncating...")
    
    # Simple truncation by character proportion
    max_chars = max_tokens * 4
    chars_to_keep_start = int(max_chars * 0.2)
    chars_to_keep_end = int(max_chars * 0.8) - 50  # account for truncation notice length
    
    truncated_transcript = (
        full_transcript[:chars_to_keep_start] +
        "\n\n... [TRANSCRIPT TRUNCATED DUE TO LENGTH] ...\n\n" +
        full_transcript[-chars_to_keep_end:]
    )
    
    final_tokens = _estimate_tokens(truncated_transcript)
    logger.info(f"Truncated transcript to estimated {final_tokens} tokens.")
    
    return truncated_transcript
