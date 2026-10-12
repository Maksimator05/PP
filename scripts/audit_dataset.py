"""Create a dataset profile markdown file."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.downloader import ensure_dataset
from retail_forecast.x5_loader import load_transactions, profile_dataset


if __name__ == "__main__":
    status = ensure_dataset()
    profile = profile_dataset(load_transactions(status.path))
    print(json.dumps(profile, ensure_ascii=False, indent=2))
