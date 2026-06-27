def resolve_conversation_state(segments: list) -> list:
    """
    Processes the chronological flow of clauses to resolve temporal conversation state.
    Flags clauses as `is_abandoned = True` if they represent incomplete thoughts,
    false starts, or get superseded by immediate self-corrections.
    """

    # Flatten all clauses to look for patterns
    # Keep track of previous clause by the same speaker
    speaker_last_clause = {}

    # Correction markers that invalidate the preceding clause
    CORRECTION_MARKERS = {
        "wait",
        "actually",
        "sorry",
        "hold on",
        "scratch that",
        "nevermind",
        "no",
    }

    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        clauses = seg.get("clauses", [])

        for clause in clauses:
            # Initialize
            clause["is_abandoned"] = False
            text = clause.get("text", "").strip()

            # Rule 1: Trailing thoughts / Interrupted speech
            if text.endswith("..."):
                clause["is_abandoned"] = True

            # Rule 2: Pure correction markers invalidate the previous clause
            # If the clause is JUST a correction marker (ignoring punctuation)
            cleaned_text = text.lower().strip(" ,.;?!")
            if cleaned_text in CORRECTION_MARKERS:
                # Invalidate the last clause spoken by this speaker
                last_clause = speaker_last_clause.get(speaker)
                if last_clause:
                    last_clause["is_abandoned"] = True

            # Update the last clause for this speaker
            speaker_last_clause[speaker] = clause

    return segments
