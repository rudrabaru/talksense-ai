import collections
import json

with open("analytics_benchmark/results/benchmark_results.json") as f:
    data = json.load(f)

fps = collections.defaultdict(list)
fns = collections.defaultdict(list)

for ds_name, ds_data in data.get("datasets", {}).items():
    for module, res in ds_data.items():
        if not isinstance(res, dict):
            continue
        for err in res.get("errors", []):
            t_type = err.get("type", "")
            text = err.get("predicted", err.get("expected", ""))
            rule = err.get("rule", "")
            if t_type == "False Positive":
                fps[module].append((text, rule, ds_name))
            elif t_type == "False Negative":
                fns[module].append((text, rule, ds_name))

print("=== FALSE POSITIVES ===")
for m, items in sorted(fps.items()):
    print(f"\n{m}: {len(items)} total")
    for text, rule, ds in items:
        print(f"  [{ds}] [{rule}] {repr(text[:100])}")

print("\n=== FALSE NEGATIVES ===")
for m, items in sorted(fns.items()):
    print(f"\n{m}: {len(items)} total")
    for text, rule, ds in items:
        print(f"  [{ds}] {repr(text[:100])}")
