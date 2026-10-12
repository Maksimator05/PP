"""CLI entrypoint for automatic X5 dataset initialization."""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.downloader import ensure_dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="try sources again when local X5 data is absent")
    args = parser.parse_args()
    status = ensure_dataset(force=args.force)
    print(f"{status.source}: {status.path} rows={status.rows} synthetic={status.is_synthetic}")
