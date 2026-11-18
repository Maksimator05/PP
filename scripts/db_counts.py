"""Print key database table row counts."""

import json
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.db import get_engine, row_counts
from retail_forecast.pipeline import KEY_TABLES


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", help="override DATABASE_URL for this count")
    args = parser.parse_args()
    print(json.dumps(row_counts(get_engine(args.database_url), KEY_TABLES), ensure_ascii=False, indent=2))
