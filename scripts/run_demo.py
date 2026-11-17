"""Run the full local demonstration pipeline."""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.pipeline import run_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="use the local SQLite fallback explicitly")
    args = parser.parse_args()
    database_url = "sqlite:///data/processed/retail_forecast.sqlite" if args.local else None
    print(run_demo(database_url=database_url))
