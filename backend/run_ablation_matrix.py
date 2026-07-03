import json
import os
import shutil
import subprocess

VARIANTS = {
    "A_Sprint_12_Sentence_Baseline": {
        "USE_SENTENCE_LEVEL_ALIGNMENT": "1",
        "DISABLE_POSTPROCESSING": "1",
        "DISABLE_5_WORD_SMOOTHING": "1",
    },
    "B_Word_Level_Only": {
        "USE_SENTENCE_LEVEL_ALIGNMENT": "0",
        "DISABLE_POSTPROCESSING": "1",
        "DISABLE_5_WORD_SMOOTHING": "1",
    },
    "C_Word_Level_and_PostProcessing": {
        "USE_SENTENCE_LEVEL_ALIGNMENT": "0",
        "DISABLE_POSTPROCESSING": "0",
        "DISABLE_5_WORD_SMOOTHING": "1",
    },
    "D_Word_Level_and_Smoothing": {
        "USE_SENTENCE_LEVEL_ALIGNMENT": "0",
        "DISABLE_POSTPROCESSING": "1",
        "DISABLE_5_WORD_SMOOTHING": "0",
    },
    "E_Word_Level_and_PostProcessing_and_Smoothing": {
        "USE_SENTENCE_LEVEL_ALIGNMENT": "0",
        "DISABLE_POSTPROCESSING": "0",
        "DISABLE_5_WORD_SMOOTHING": "0",
    },
}


def run_benchmark(variant_name, env_vars):
    print(f"\n{'='*60}\nRUNNING VARIANT: {variant_name}\n{'='*60}")

    # Setup environment
    env = os.environ.copy()
    for k, v in env_vars.items():
        env[k] = v

    cmd = ["venv\\Scripts\\python.exe", "run_full_benchmark.py"]

    # Run the benchmark
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError:
        print(f"ERROR: Benchmark failed for {variant_name}")
        return False

    # Move results
    if os.path.exists("benchmark_results.json"):
        shutil.copy("benchmark_results.json", f"benchmark_results_{variant_name}.json")
    if os.path.exists("benchmark_results_report.md"):
        shutil.copy(
            "benchmark_results_report.md", f"benchmark_report_{variant_name}.md"
        )

    return True


def main():
    results_summary = {}

    for name, env_vars in VARIANTS.items():
        success = run_benchmark(name, env_vars)
        if success:
            with open(f"benchmark_results_{name}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                results_summary[name] = data["aggregate"]
        else:
            results_summary[name] = {"error": "Benchmark failed"}

    print("\n\nFINAL ABLATION RESULTS:\n")
    for name, agg in results_summary.items():
        if "error" in agg:
            print(f"{name}: FAILED")
        else:
            print(f"{name}:")
            print(f"  F1:   {agg.get('avg_macro_f1', 0)}")
            print(f"  Acc:  {agg.get('avg_accuracy', 0)}%")
            print(f"  SCDR: {agg.get('avg_scdr', 0)}%")
            print(
                f"  Boundary Err (Avg/Med/P90): {agg.get('boundary_error_avg_ms', 0)}ms / {agg.get('boundary_error_median_ms', 0)}ms / {agg.get('boundary_error_p90_ms', 0)}ms"
            )
            print(
                f"  Transitions: GT={agg.get('total_gt_transitions', 0)} | Pred={agg.get('total_pred_transitions', 0)} | TP={agg.get('total_tp', 0)} | FN={agg.get('total_fn', 0)} | FP={agg.get('total_fp', 0)} | WrongSpk={agg.get('total_wrong_spk', 0)}"
            )
            print(
                f"  Transition Precision: {agg.get('scdr_precision', 0):.4f} | Recall: {agg.get('scdr_recall', 0):.4f} | F1: {agg.get('scdr_f1', 0):.4f}"
            )
            print(
                f"  <100ms: {agg.get('within_100ms', 0)}%  <250ms: {agg.get('within_250ms', 0)}%  <500ms: {agg.get('within_500ms', 0)}%"
            )
            print("")


if __name__ == "__main__":
    main()
