import json

with open("utils/keywords_config.json") as f:
    d = json.load(f)
print("=== Sales Objections ===")
print(json.dumps(d.get("sales", {}).get("objections", {}), indent=2))
print("\n=== Meeting Actions ===")
print(json.dumps(d.get("meeting", {}).get("actions", []), indent=2))
print("\n=== Meeting Ownership Commitment ===")
print(json.dumps(d.get("meeting", {}).get("ownership_commitment", []), indent=2))
