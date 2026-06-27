import os
import sys

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analytics_benchmark.dataset_loader import discover_datasets, load_dataset

# Evaluators
from analytics_benchmark.evaluators import (
    action_items,
    buying_signals,
    commitments,
    decisions,
    objections,
    sentiment,
)
from analytics_benchmark.reports import generate_reports


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "datasets")
    output_dir = os.path.join(os.path.dirname(__file__), "results")

    datasets = discover_datasets(base_dir)
    print(f"Discovered {len(datasets)} datasets.")

    results = {
        "total_datasets": len(datasets),
        "datasets": {},
        "overall_metrics": {},
        "all_errors": [],
    }

    overall_tp = {
        "action_items": 0,
        "decisions": 0,
        "objections": 0,
        "buying_signals": 0,
        "commitments": 0,
        "sentiment": 0,
    }
    overall_fp = {
        "action_items": 0,
        "decisions": 0,
        "objections": 0,
        "buying_signals": 0,
        "commitments": 0,
        "sentiment": 0,
    }
    overall_fn = {
        "action_items": 0,
        "decisions": 0,
        "objections": 0,
        "buying_signals": 0,
        "commitments": 0,
        "sentiment": 0,
    }

    for path in datasets:
        dataset = load_dataset(path)
        dataset_id = os.path.basename(path).replace(".json", "")
        mode = dataset.get("mode", "meeting")
        print(f"Evaluating {dataset_id} ({mode})...")

        ds_results = {}

        # Run Action Items
        ai_res = action_items.evaluate(dataset)
        ds_results["action_items"] = ai_res
        overall_tp["action_items"] += ai_res["true_positives"]
        overall_fp["action_items"] += ai_res["false_positives"]
        overall_fn["action_items"] += ai_res["false_negatives"]

        # Run Decisions
        dec_res = decisions.evaluate(dataset)
        ds_results["decisions"] = dec_res
        overall_tp["decisions"] += dec_res["true_positives"]
        overall_fp["decisions"] += dec_res["false_positives"]
        overall_fn["decisions"] += dec_res["false_negatives"]

        # Run Objections (mainly for sales, but can run on all or check mode)
        obj_res = objections.evaluate(dataset)
        ds_results["objections"] = obj_res
        overall_tp["objections"] += obj_res["true_positives"]
        overall_fp["objections"] += obj_res["false_positives"]
        overall_fn["objections"] += obj_res["false_negatives"]

        # Run Buying Signals
        buy_res = buying_signals.evaluate(dataset)
        ds_results["buying_signals"] = buy_res
        overall_tp["buying_signals"] += buy_res["true_positives"]
        overall_fp["buying_signals"] += buy_res["false_positives"]
        overall_fn["buying_signals"] += buy_res["false_negatives"]

        # Run Commitments
        com_res = commitments.evaluate(dataset)
        ds_results["commitments"] = com_res
        overall_tp["commitments"] += com_res["true_positives"]
        overall_fp["commitments"] += com_res["false_positives"]
        overall_fn["commitments"] += com_res["false_negatives"]

        # Run Sentiment
        sen_res = sentiment.evaluate(dataset)
        ds_results["sentiment"] = sen_res
        overall_tp["sentiment"] += sen_res["true_positives"]
        overall_fp["sentiment"] += sen_res["false_positives"]
        overall_fn["sentiment"] += sen_res["false_negatives"]

        results["datasets"][dataset_id] = ds_results

        # Aggregate errors
        for mod_name, mod_res in ds_results.items():
            for err in mod_res.get("errors", []):
                err_copy = dict(err)
                err_copy["dataset_id"] = dataset_id
                err_copy["module"] = mod_name
                results["all_errors"].append(err_copy)

    # Calculate overall F1
    for module in overall_tp.keys():
        tp = overall_tp[module]
        fp = overall_fp[module]
        fn = overall_fn[module]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        results["overall_metrics"][module] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

    generate_reports(results, output_dir)


if __name__ == "__main__":
    main()
