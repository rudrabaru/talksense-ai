import re
from typing import List, Dict, Any, Tuple

def _tokenize(text: str) -> set:
    text = str(text).lower()
    tokens = re.findall(r'\b\w+\b', text)
    return set(tokens)

def compute_overlap(text1: str, text2: str) -> float:
    set1 = _tokenize(text1)
    set2 = _tokenize(text2)
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    # Jaccard index based on the smaller set (we want to reward if the predicted phrase is fully contained or vice versa)
    overlap = len(intersection) / min(len(set1), len(set2))
    return overlap

def evaluate_list_matches(predicted: List[str], expected: List[str], threshold: float = 0.5) -> Dict[str, Any]:
    """
    Evaluates two lists of strings using token overlap matching.
    Returns TP, FP, FN, Precision, Recall, F1, and matched details.
    """
    tp = 0
    fp = 0
    fn = 0
    
    matched_expected = set()
    matches = []
    errors = []

    # Calculate True Positives and False Positives
    for pred in predicted:
        best_match = None
        best_score = 0.0
        best_idx = -1
        
        for i, exp in enumerate(expected):
            if i in matched_expected:
                continue
            score = compute_overlap(pred, exp)
            if score > best_score:
                best_score = score
                best_match = exp
                best_idx = i
                
        if best_score >= threshold:
            tp += 1
            matched_expected.add(best_idx)
            matches.append({
                "predicted": pred,
                "expected": best_match,
                "score": round(best_score, 2)
            })
        else:
            fp += 1
            errors.append({
                "type": "False Positive",
                "predicted": pred,
                "reason": "No expected item matched"
            })

    # Calculate False Negatives
    for i, exp in enumerate(expected):
        if i not in matched_expected:
            fn += 1
            errors.append({
                "type": "False Negative",
                "expected": exp,
                "reason": "Missed by predictor"
            })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "matches": matches,
        "errors": errors
    }

def evaluate_exact_dict(predicted: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates key-value exact matches (e.g. sentiment counts).
    """
    tp = 0
    fp = 0
    fn = 0
    
    matches = []
    errors = []

    all_keys = set(predicted.keys()).union(set(expected.keys()))
    
    for key in all_keys:
        pred_val = predicted.get(key, 0)
        exp_val = expected.get(key, 0)
        
        # Absolute difference approach for counts
        diff = pred_val - exp_val
        if diff == 0:
            tp += exp_val
            if exp_val > 0:
                matches.append({"key": key, "expected": exp_val, "predicted": pred_val})
        elif diff > 0:
            tp += exp_val
            fp += diff
            errors.append({"type": "False Positive", "key": key, "expected": exp_val, "predicted": pred_val})
        else: # diff < 0
            tp += pred_val
            fn += abs(diff)
            errors.append({"type": "False Negative", "key": key, "expected": exp_val, "predicted": pred_val})

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "matches": matches,
        "errors": errors
    }
