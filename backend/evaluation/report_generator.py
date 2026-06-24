import json
import os
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.thresholds import evaluate_thresholds, THRESHOLDS

def generate_report():
    metrics_path = os.path.join(os.path.dirname(__file__), "reports", "latest_metrics.json")
    if not os.path.exists(metrics_path):
        print(f"Error: {metrics_path} not found. Run evaluate_analytics.py first.")
        return

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    health = evaluate_thresholds(metrics)

    report_path = os.path.join(os.path.dirname(__file__), "reports", "analytics_accuracy_report.md")

    # Build Executive Summary
    lines = [
        "# Analytics Accuracy Report",
        f"> Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Executive Summary",
        "| Component | Status |",
        "|-----------|--------|"
    ]

    for component, status in health.items():
        icon = "✅ PASS" if status == "PASS" else "❌ FAIL"
        lines.append(f"| {component.replace('_', ' ').title()} | {icon} |")

    lines.extend([
        "",
        "## Component Scores"
    ])

    for comp, data in metrics.items():
        lines.append(f"### {comp.replace('_', ' ').title()}")
        if "error" in data:
            lines.append(f"**Error**: {data['error']}\n")
            continue
        
        for key, val in data.items():
            if key != "confusion_matrix":
                # Handle percentages or floats
                if isinstance(val, float):
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {val:.3f}")
                else:
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {val}")
        lines.append("")

    lines.extend([
        "## Weakest Components",
        "The following components failed to meet the production thresholds:"
    ])
    
    failed_components = [c for c, s in health.items() if s == "FAIL"]
    if not failed_components:
        lines.append("- *None! All components are passing.*")
    else:
        for c in failed_components:
            lines.append(f"- **{c.replace('_', ' ').title()}**")

    lines.extend([
        "",
        "## Recommended Actions"
    ])

    for c in failed_components:
        lines.append(f"- **{c.replace('_', ' ').title()}** fell below threshold. Recommendation: Do not use for downstream analytics until models are improved or replaced with LLM alternatives.")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report generated at {report_path}")

if __name__ == "__main__":
    generate_report()
