"""Print key database table row counts."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.db import get_engine, row_counts
from retail_forecast.pipeline import KEY_TABLES


if __name__ == "__main__":
    print(json.dumps(row_counts(get_engine(), KEY_TABLES), ensure_ascii=False, indent=2))
