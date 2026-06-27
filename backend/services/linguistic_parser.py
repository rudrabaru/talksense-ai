import re

from services.clause_parser import split_into_clauses

# Negation words
NEGATION_TOKENS = {
    "not",
    "never",
    "no",
    "cannot",
    "won't",
    "wouldn't",
    "shouldn't",
    "don't",
    "isn't",
    "wasn't",
    "didn't",
    "aren't",
}

# Conditional phrases (including multi-word phrases)
CONDITIONAL_TOKENS = {
    "if",
    "unless",
    "provided that",
    "assuming",
    "would",
    "could",
    "might",
    "depending on",
}


def _tokenize(text: str) -> set:
    text = str(text).lower()
    # Simple tokenization for single words
    tokens = re.findall(r"\b\w+(?:'\w+)?\b", text)
    return set(tokens)


def annotate_segments(segments: list) -> list:
    """
    Annotates a list of segment dictionaries in-place with a clauses array.
    """
    for seg in segments:
        text = seg.get("text", "")
        seg["clauses"] = split_into_clauses(text)

    return segments
