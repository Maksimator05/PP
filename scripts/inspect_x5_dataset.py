"""Inspect local X5 RetailHero files and write a profile."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.pipeline import inspect_x5


if __name__ == "__main__":
    print(inspect_x5())
