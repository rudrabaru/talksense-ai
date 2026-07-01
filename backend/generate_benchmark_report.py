import os
import sys


def parse_scorecard(filepath):
    metrics = {}
    if not os.path.exists(filepath):
        return metrics

    with open(filepath, "r") as f:
        for line in f:
            if (
                "|" in line
                and not line.startswith("| Metric")
                and not line.startswith("| :---")
            ):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    metric_name = parts[1]
                    try:
                        value = float(parts[2].replace("%", "").strip())
                        metrics[metric_name] = value
                    except ValueError:
                        if parts[2].lower() in ["true", "false"]:
                            metrics[metric_name] = parts[2].lower() == "true"
                        else:
                            metrics[metric_name] = parts[2]
    return metrics


def generate_report(current_metrics, previous_metrics):
    thresholds = {
        "Word_Error_Rate": {
            "op": "<",
            "limit": 15.0,
            "name": "WER",
            "format": "{:.2f}%",
        },
        "Character_Error_Rate": {
            "op": "<",
            "limit": 10.0,
            "name": "CER",
            "format": "{:.2f}%",
        },
        "avg_accuracy": {
            "op": ">",
            "limit": 80.0,
            "name": "Speaker Accuracy",
            "format": "{:.2f}%",
        },
        "avg_macro_f1": {
            "op": ">",
            "limit": 0.75,
            "name": "Macro F1 (Speaker)",
            "format": "{:.2f}",
        },
        "Macro_F1": {
            "op": ">",
            "limit": 0.75,
            "name": "Macro F1 (Role)",
            "format": "{:.2f}",
        },
        "Host_Accuracy": {
            "op": ">",
            "limit": 90.0,
            "name": "Role Accuracy (Host)",
            "format": "{:.2f}%",
        },
        "Guest_Accuracy": {
            "op": ">",
            "limit": 90.0,
            "name": "Role Accuracy (Guest)",
            "format": "{:.2f}%",
        },
        "Action_Item_Precision": {
            "op": ">",
            "limit": 80.0,
            "name": "Action Item Precision",
            "format": "{:.2f}%",
        },
        "Objection_Detection_Precision": {
            "op": ">",
            "limit": 85.0,
            "name": "Objection Precision",
            "format": "{:.2f}%",
        },
    }

    informational = {
        "avg_scdr": {"name": "SCDR", "format": "{:.2f}%"},
        "Avg_Latency_ms": {"name": "Average Inference Latency", "format": "{:.0f} ms"},
        "Peak_Memory_MB": {"name": "Peak Memory Usage", "format": "{:.2f} MB"},
    }

    report_lines = []
    report_lines.append("# Continuous Benchmark & Model Evaluation Report")
    report_lines.append("")
    report_lines.append("## Production Threshold Validation")
    report_lines.append("| Metric | Current | Previous | Delta | Threshold | Status |")
    report_lines.append("|---|---|---|---|---|---|")

    passed = True
    regressions = []

    for key, rule in thresholds.items():
        if key not in current_metrics:
            continue

        cur_val = current_metrics[key]
        prev_val = previous_metrics.get(key, None)
        limit = rule["limit"]
        op = rule["op"]
        name = rule["name"]
        fmt = rule["format"]

        # Calculate Delta
        delta_str = "-"
        if prev_val is not None and isinstance(prev_val, (int, float)):
            delta = cur_val - prev_val
            if delta > 0:
                delta_str = f"+{delta:.2f}"
            elif delta < 0:
                delta_str = f"{delta:.2f}"
            else:
                delta_str = "0.00"

        # Check condition
        if op == "<":
            success = cur_val < limit
            op_str = f"< {limit}"
        else:
            success = cur_val > limit
            op_str = f"> {limit}"

        status = "✅ PASS" if success else "❌ FAIL"
        if not success:
            passed = False
            regressions.append(f"{name} regressed to {cur_val} (Requires {op_str})")

        cur_str = fmt.format(cur_val)
        prev_str = fmt.format(prev_val) if prev_val is not None else "N/A"

        report_lines.append(
            f"| {name} | **{cur_str}** | {prev_str} | {delta_str} | {op_str} | {status} |"
        )

    report_lines.append("")
    report_lines.append("## Informational & Performance Metrics")
    report_lines.append("| Metric | Current | Previous | Delta |")
    report_lines.append("|---|---|---|---|")

    for key, info in informational.items():
        if key not in current_metrics:
            continue
        cur_val = current_metrics[key]
        prev_val = previous_metrics.get(key, None)
        name = info["name"]
        fmt = info["format"]

        delta_str = "-"
        if prev_val is not None and isinstance(prev_val, (int, float)):
            delta = cur_val - prev_val
            if delta > 0:
                delta_str = f"+{delta:.2f}"
            elif delta < 0:
                delta_str = f"{delta:.2f}"
            else:
                delta_str = "0.00"

        cur_str = fmt.format(cur_val)
        prev_str = fmt.format(prev_val) if prev_val is not None else "N/A"

        report_lines.append(f"| {name} | **{cur_str}** | {prev_str} | {delta_str} |")

    report_lines.append("")
    report_lines.append("## Summary")
    if passed:
        report_lines.append(
            "✅ **All production thresholds passed.** The models are performing within required tolerances."
        )
    else:
        report_lines.append(
            "❌ **REGRESSION DETECTED.** One or more production thresholds were violated:"
        )
        for r in regressions:
            report_lines.append(f"- {r}")

    with open("benchmark_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return passed


if __name__ == "__main__":
    current_scorecard = "final_scorecard.md"
    previous_scorecard = "previous_scorecard.md"

    cur_metrics = parse_scorecard(current_scorecard)
    prev_metrics = parse_scorecard(previous_scorecard)

    passed = generate_report(cur_metrics, prev_metrics)

    if not passed:
        print("Validation Failed! See benchmark_report.md for details.")
        sys.exit(1)
    else:
        print("Validation Passed! Report generated at benchmark_report.md")
        sys.exit(0)
