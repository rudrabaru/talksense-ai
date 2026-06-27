import os
import sys
from typing import Any, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from analytics_benchmark.metrics import evaluate_list_matches
from services.context_analyzer import BUDGET_ALIGNMENT_KEYWORDS, BUYING_SIGNAL_KEYWORDS
from services.conversation_state_resolver import resolve_conversation_state
from services.linguistic_parser import annotate_segments


def evaluate(dataset: Dict[str, Any]) -> Dict[str, Any]:
    segments = dataset.get("segments", [])
    expected_texts = dataset.get("expected_buying_signals", [])

    # Combined buying signal keywords — matches what ConversationEngine uses (buying_signal phrases + budget alignment)
    ALL_BUYING_KEYWORDS = (
        list(BUYING_SIGNAL_KEYWORDS)
        + list(BUDGET_ALIGNMENT_KEYWORDS)
        + ["interested", "this looks good", "sounds good", "makes sense"]
    )

    annotate_segments(segments)
    resolve_conversation_state(segments)
    predicted_texts = []
    for s in segments:
        for c in s.get("clauses", []):
            if (
                not c.get("is_negated")
                and not c.get("is_conditional")
                and not c.get("is_abandoned")
                and any(kw in c.get("text", "").lower() for kw in ALL_BUYING_KEYWORDS)
            ):
                predicted_texts.append(c.get("text", ""))

    # Evaluate
    results = evaluate_list_matches(predicted_texts, expected_texts, threshold=0.5)

    # Add explainability
    for i, err in enumerate(results.get("errors", [])):
        if err["type"] == "False Positive":
            pred_text = err["predicted"]
            source_idx = -1
            speaker = "Unknown"
            for idx, seg in enumerate(segments):
                if pred_text.lower() in seg.get("text", "").lower():
                    source_idx = idx
                    speaker = seg.get("speaker", "Unknown")
                    break

            results["errors"][i]["segment_idx"] = source_idx
            results["errors"][i]["speaker"] = speaker
            results["errors"][i]["rule"] = "BUYING_SIGNAL_KEYWORDS"

    return results
