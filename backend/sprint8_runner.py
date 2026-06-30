import subprocess
import json
import os
import time


def run_benchmark(env_vars, name):
    print(f"\n==============================")
    print(f"Running Benchmark: {name}")
    print(f"==============================")
    env = os.environ.copy()
    env.update(env_vars)

    cmd = [r"venv\Scripts\python.exe", "run_full_benchmark.py"]
    proc = subprocess.Popen(
        cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    for line in proc.stdout:
        print(line, end="")
    proc.wait()

    result_path = "benchmark_results.json"
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            return json.load(f)["aggregate"]
    return None


def main():
    results = {}

    configs = {
        "Phase 1: Baseline": {},
        "Phase 1: Strict Pyannote Cluster Threshold (0.7)": {
            "PYANNOTE_CLUSTERING_THRESHOLD": "0.7"
        },
        "Phase 1: Loose Pyannote Cluster Threshold (0.5)": {
            "PYANNOTE_CLUSTERING_THRESHOLD": "0.5"
        },
        "Phase 1: Long Min Duration Off (0.5)": {"PYANNOTE_MIN_DURATION_OFF": "0.5"},
    }

    for name, config in configs.items():
        results[name] = run_benchmark(config, name)

    best_pyannote = {
        "PYANNOTE_CLUSTERING_THRESHOLD": "0.7",
        "PYANNOTE_MIN_DURATION_OFF": "0.5",
    }

    phase2_config = {"FILTER_SHORT_UTTERANCES_S": "0.5"}
    results["Phase 2: Short Utterance Filtering (0.5s)"] = run_benchmark(
        phase2_config, "Phase 2: Short Utterance Filtering"
    )

    phase3_config = {"STRICT_VAD_PREFILTER": "1"}
    results["Phase 3: Strict VAD Prefilter"] = run_benchmark(
        phase3_config, "Phase 3: VAD Prefilter"
    )

    combined_config = {}
    combined_config.update(best_pyannote)
    combined_config.update(phase2_config)
    combined_config.update(phase3_config)
    results["Phase 4: Combined Optimization"] = run_benchmark(
        combined_config, "Phase 4: Combined"
    )

    with open("sprint8_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n\nAll benchmarks completed. Results written to sprint8_results.json")


if __name__ == "__main__":
    main()
