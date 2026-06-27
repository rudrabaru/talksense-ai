import re

# Discourse markers and conjunctions that indicate a clause boundary
CLAUSE_BOUNDARIES = [
    "but",
    "however",
    "although",
    "though",
    "because",
    "if",
    "unless",
    "while",
    "except",
    "instead",
    "wait",
    "actually",
    "sorry",
]

# Negation and conditional tokens for individual clauses
NEGATION_TOKENS = {
    "not",
    "never",
    "no",
    "cannot",
    "won't",
    "wouldn't",
    "shouldn't",
    "don't",
    "doesn't",
    "isn't",
    "wasn't",
    "didn't",
    "aren't",
}

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
    tokens = re.findall(r"\b\w+(?:'\w+)?\b", text)
    return set(tokens)


def split_into_clauses(text: str) -> list:
    """
    Splits text into logical clauses based on punctuation and discourse markers.
    Returns a list of dictionaries with clause metadata.
    """
    original_text = str(text)

    # 1. Split on punctuation (. ; ? !)
    # Use lookbehind to keep punctuation with the clause, or just split
    parts = re.split(r"([.;?!]+)", original_text)

    # Recombine text and punctuation
    raw_sentences = []
    for i in range(0, len(parts) - 1, 2):
        raw_sentences.append((parts[i] + parts[i + 1]).strip())
    if len(parts) % 2 != 0 and parts[-1].strip():
        raw_sentences.append(parts[-1].strip())

    if not raw_sentences:
        if original_text.strip():
            raw_sentences = [original_text.strip()]
        else:
            return []

    # 2. Split each sentence on discourse boundaries
    boundary_pattern = r"\b(" + "|".join(CLAUSE_BOUNDARIES) + r")\b"

    clauses_data = []
    order = 0

    for sentence in raw_sentences:
        splits = re.split(boundary_pattern, sentence, flags=re.IGNORECASE)

        current_clause = splits[0]
        for i in range(1, len(splits) - 1, 2):
            # splits[i] is the marker, splits[i+1] is the rest
            current_clause += splits[i]
            if current_clause.strip():
                clauses_data.append(current_clause.strip())
            current_clause = splits[i + 1]

        if current_clause.strip():
            clauses_data.append(current_clause.strip())

    # 3. Annotate clauses
    results = []
    for clause_text in clauses_data:
        text_lower = clause_text.lower()
        tokens = _tokenize(text_lower)

        is_neg = bool(NEGATION_TOKENS.intersection(tokens))

        is_cond = False
        for cond in CONDITIONAL_TOKENS:
            if " " in cond:
                if cond in text_lower:
                    is_cond = True
                    break
            else:
                if cond in tokens:
                    is_cond = True
                    break

        results.append(
            {
                "text": clause_text,
                "is_negated": is_neg,
                "is_conditional": is_cond,
                "clause_order": order,
            }
        )
        order += 1

    return results
