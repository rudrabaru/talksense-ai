import json
import os
from collections import Counter
from typing import Dict, Any
from typing import Dict, Any

def generate_reports(results: Dict[str, Any], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON report
    json_path = os.path.join(output_dir, "benchmark_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Generate Markdown report
    md_path = os.path.join(output_dir, "benchmark_report.md")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Analytics Benchmark Report\n\n")
        
        # Overall Summary
        f.write("## Overall Summary\n")
        f.write(f"- **Total Datasets Evaluated:** {results.get('total_datasets', 0)}\n")
        
        overall = results.get("overall_metrics", {})
        f.write("### Aggregate Metrics\n")
        f.write("| Module | Precision | Recall | F1 Score |\n")
        f.write("|--------|-----------|--------|----------|\n")
        for module, mets in overall.items():
            f.write(f"| {module.capitalize()} | {mets.get('precision', 0):.3f} | {mets.get('recall', 0):.3f} | {mets.get('f1', 0):.3f} |\n")
        f.write("\n")
        
        # Failure Analysis
        f.write("## Failure Analysis\n")
        all_errors = results.get("all_errors", [])
        
        fp_counter = Counter([e.get("predicted") for e in all_errors if e.get("type") == "False Positive"])
        fn_counter = Counter([e.get("expected") for e in all_errors if e.get("type") == "False Negative"])
        
        f.write("### Top Recurring False Positives (Incorrect Extractions)\n")
        if not fp_counter:
            f.write("- None\n")
        for phrase, count in fp_counter.most_common(10):
            f.write(f"- **{count}x**: *\"{phrase}\"*\n")
            
        f.write("\n### Top Recurring False Negatives (Missed by Engine)\n")
        if not fn_counter:
            f.write("- None\n")
        for phrase, count in fn_counter.most_common(10):
            f.write(f"- **{count}x**: *\"{phrase}\"*\n")
        f.write("\n")
        
        # Detailed Results
        f.write("## Detailed Results\n")
        for dataset_id, dataset_res in results.get("datasets", {}).items():
            f.write(f"### Dataset: `{dataset_id}`\n")
            
            for module, mets in dataset_res.items():
                f.write(f"#### {module.capitalize()}\n")
                f.write(f"- **F1:** {mets.get('f1', 0)} (P: {mets.get('precision', 0)}, R: {mets.get('recall', 0)})\n")
                f.write(f"- **TP:** {mets.get('true_positives', 0)}, **FP:** {mets.get('false_positives', 0)}, **FN:** {mets.get('false_negatives', 0)}\n")
                
                matches = mets.get("matches", [])
                if matches:
                    f.write("- **True Positives (Matches):**\n")
                    for m in matches:
                        f.write(f"  - Predicted: *{m.get('predicted')}* | Expected: *{m.get('expected')}*\n")
                        
                errors = mets.get("errors", [])
                if errors:
                    f.write("- **Errors:**\n")
                    for err in errors:
                        if err.get('type') == 'False Positive':
                            f.write(f"  - 🔴 **FP:** Predicted *{err.get('predicted')}* (Rule: {err.get('rule', 'N/A')})\n")
                        elif err.get('type') == 'False Negative':
                            f.write(f"  - 🟡 **FN:** Missed *{err.get('expected')}*\n")
            f.write("\n")
            
    print(f"\n[SUCCESS] Reports generated in {output_dir}")
    print(f"  - {json_path}")
    print(f"  - {md_path}")
