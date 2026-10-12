"""Load and aggregate history into local processed files."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.downloader import ensure_dataset
from retail_forecast.x5_loader import load_transactions


if __name__ == "__main__":
    status = ensure_dataset()
    transactions = load_transactions(status.path)
    weekly = aggregate_weekly_sales(transactions)
    weekly.to_csv("data/processed/weekly_sales.csv", index=False)
    print(f"Loaded weekly rows: {len(weekly)}")
