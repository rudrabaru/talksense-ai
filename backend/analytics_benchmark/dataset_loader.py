import json
import os
from typing import Dict, List, Any

def load_dataset(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for seg in data.get("segments", []):
            if "sentiment_confidence" not in seg:
                seg["sentiment_confidence"] = 1.0
        return data

def discover_datasets(base_dir: str) -> List[str]:
    """Discover all JSON datasets in the datasets directory."""
    datasets = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                datasets.append(os.path.join(root, file))
    return datasets
