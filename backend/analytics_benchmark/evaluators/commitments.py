import sys
import os
from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from services.context_analyzer import detect_ownership_committed, OWNERSHIP_COMMITMENT_KEYWORDS, COMMITMENT_KEYWORDS
from services.linguistic_parser import annotate_segments
from services.conversation_state_resolver import resolve_conversation_state
from services.intent_resolver import resolve_clause_intent, ROADMAP_STATEMENT
from analytics_benchmark.metrics import evaluate_list_matches

def evaluate(dataset: Dict[str, Any]) -> Dict[str, Any]:
    segments = dataset.get("segments", [])
    expected_texts = dataset.get("expected_commitments", [])
    
    # Combined keyword list: match ownership/personal commitment phrases AND end-of-call commitment phrases
    ALL_COMMITMENT_PATTERNS = set(list(OWNERSHIP_COMMITMENT_KEYWORDS) + list(COMMITMENT_KEYWORDS))
    
    predicted_texts = []
    annotate_segments(segments)
    resolve_conversation_state(segments)
    # Replicate detection but extract text
    for seg in segments:
        for clause in seg.get("clauses", []):
            if clause.get("is_negated") or clause.get("is_conditional") or clause.get("is_abandoned"):
                continue
            # Skip roadmap statements (not personal commitments)
            intent_result = resolve_clause_intent(clause.get("text", ""), clause)
            if intent_result["intent"] == ROADMAP_STATEMENT:
                continue
            text = clause.get("text", "").lower()
            if any(pattern in text for pattern in ALL_COMMITMENT_PATTERNS):
                predicted_texts.append(clause.get("text", ""))
    
    # Evaluate
    results = evaluate_list_matches(predicted_texts, expected_texts, threshold=0.5)
    
    # Add explainability
    for i, err in enumerate(results.get("errors", [])):
        if err["type"] == "False Positive":
            pred_text = err["predicted"]
            source_idx = -1
            speaker = "Unknown"
            rule = "Unknown"
            
            for idx, seg in enumerate(segments):
                if pred_text.lower() in seg.get("text", "").lower():
                    source_idx = idx
                    speaker = seg.get("speaker", "Unknown")
                    for pattern in OWNERSHIP_COMMITMENT_KEYWORDS:
                        if pattern in pred_text.lower():
                            rule = f"Pattern: {pattern}"
                            break
                    break
            
            results["errors"][i]["segment_idx"] = source_idx
            results["errors"][i]["speaker"] = speaker
            results["errors"][i]["rule"] = rule
            
    return results
