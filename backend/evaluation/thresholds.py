THRESHOLDS = {
    "speaker_attribution_macro_f1": 0.75,
    "speaker_attribution_coverage": 0.80,
    "role_classification_macro_f1": 0.70,
    "buying_signal_f1": 0.70,
    "objection_f1": 0.70,
    "objection_handling_accuracy": 0.70,
}


def evaluate_thresholds(metrics: dict) -> dict:
    """
    Given a metrics dictionary from evaluate_analytics.py,
    return a PASS/FAIL status for each subsystem.
    """
    health = {
        "speaker_attribution": "FAIL",
        "role_classification": "FAIL",
        "buying_signals": "FAIL",
        "objections": "FAIL",
        "objection_handling": "FAIL",
    }

    # Speaker Attribution
    sa_metrics = metrics.get("speaker_attribution", {})
    if sa_metrics:
        if (
            sa_metrics.get("macro_f1", 0) >= THRESHOLDS["speaker_attribution_macro_f1"]
            and sa_metrics.get("coverage", 0)
            >= THRESHOLDS["speaker_attribution_coverage"]
        ):
            health["speaker_attribution"] = "PASS"

    # Role Classification
    rc_metrics = metrics.get("role_classification", {})
    if rc_metrics:
        if rc_metrics.get("macro_f1", 0) >= THRESHOLDS["role_classification_macro_f1"]:
            health["role_classification"] = "PASS"

    # Buying Signals
    bs_metrics = metrics.get("buying_signals", {})
    if bs_metrics:
        if bs_metrics.get("f1", 0) >= THRESHOLDS["buying_signal_f1"]:
            health["buying_signals"] = "PASS"

    # Objections
    obj_metrics = metrics.get("objections", {})
    if obj_metrics:
        if obj_metrics.get("f1", 0) >= THRESHOLDS["objection_f1"]:
            health["objections"] = "PASS"

    # Objection Handling
    oh_metrics = metrics.get("objection_handling", {})
    if oh_metrics:
        if oh_metrics.get("accuracy", 0) >= THRESHOLDS["objection_handling_accuracy"]:
            health["objection_handling"] = "PASS"

    return health
