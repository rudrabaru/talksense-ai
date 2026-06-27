import os
import sys
from typing import Any, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from analytics_benchmark.metrics import evaluate_list_matches
from services.context_analyzer import detect_decisions


def evaluate(dataset: Dict[str, Any]) -> Dict[str, Any]:
    segments = dataset.get("segments", [])
    expected_texts = dataset.get("expected_decisions", [])

    # Run the real extractor
    predicted_objs = detect_decisions(segments)
    predicted_decisions = [obj.get("text", "") for obj in predicted_objs]

    # Evaluate
    results = evaluate_list_matches(predicted_decisions, expected_texts, threshold=0.5)

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
            results["errors"][i]["rule"] = "DECISION_PATTERNS"

    return results
