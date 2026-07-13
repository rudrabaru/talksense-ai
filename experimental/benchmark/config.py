import os
from pathlib import Path

# Paths
BENCHMARK_ROOT = Path(__file__).parent
PROJECT_ROOT = BENCHMARK_ROOT.parent.parent

DATASET_DIR = BENCHMARK_ROOT / "dataset"
REPORTS_DIR = BENCHMARK_ROOT / "reports"

# Diart execution config
DIART_IMAGE = "talksense-diart-cpu"
DIART_DEVICE = "cpu"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Ensure directories exist
for sub_dir in ["interview", "meeting", "sales"]:
    (DATASET_DIR / sub_dir).mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
