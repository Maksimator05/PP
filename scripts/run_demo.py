"""Run the full local demonstration pipeline."""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.pipeline import run_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="use the local SQLite fallback explicitly")
    parser.add_argument("--database-url", help="override DATABASE_URL for this run")
    args = parser.parse_args()
    if args.local and args.database_url:
        parser.error("--local and --database-url cannot be combined")
    database_url = "sqlite:///data/processed/retail_forecast.sqlite" if args.local else args.database_url
    print(run_demo(database_url=database_url))
