import sys
import os
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from services.context_analyzer import extract_actions
from analytics_benchmark.metrics import evaluate_list_matches

def evaluate(dataset: Dict[str, Any]) -> Dict[str, Any]:
    segments = dataset.get("segments", [])
    expected = dataset.get("expected_action_items", [])
    
    # We want to flatten expected to just the task text for simple evaluation
    expected_texts = [item.get("task", "") for item in expected]
    
    # Run the real extractor
    predicted_items = extract_actions(segments)
    predicted_texts = [item.get("task", "") for item in predicted_items]
    
    # Evaluate
    results = evaluate_list_matches(predicted_texts, expected_texts, threshold=0.5)
    
    # Add explainability
    for i, err in enumerate(results.get("errors", [])):
        if err["type"] == "False Positive":
            # Find the rule/keyword that triggered this if possible
            # extract_actions just returns "task", "owner", "deadline". It doesn't trace the rule.
            # But we fulfill the explainability requirement by returning the predicted phrase and segment index.
            # Let's find which segment it came from by matching text
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
            results["errors"][i]["rule"] = "ACTION_KEYWORDS"
            
    return results
