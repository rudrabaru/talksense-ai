import os
import sys
from typing import Any, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from analytics_benchmark.metrics import evaluate_exact_dict
from services.context_analyzer import aggregate_sentiment


def evaluate(dataset: Dict[str, Any]) -> Dict[str, Any]:
    segments = dataset.get("segments", [])
    expected = dataset.get(
        "expected_sentiment", {"Positive": 0, "Neutral": 0, "Negative": 0}
    )

    # Run the real extractor
    predicted = aggregate_sentiment(segments)

    # Evaluate
    results = evaluate_exact_dict(predicted, expected)

    # Add explainability (not as simple for aggregations, but we can list the keys that mismatched)
    for i, err in enumerate(results.get("errors", [])):
        results["errors"][i]["rule"] = "SENTIMENT_AGGREGATION"
        results["errors"][i]["segment_idx"] = -1
        results["errors"][i]["speaker"] = "N/A"

    return results
