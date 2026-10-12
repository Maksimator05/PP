"""Verify that local X5 RetailHero files are readable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.downloader import verify_x5_dataset


if __name__ == "__main__":
    status = verify_x5_dataset()
    print(f"verified source={status.source} path={status.path} rows={status.rows}")
