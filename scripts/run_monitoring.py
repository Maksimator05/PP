"""Run a small drift monitoring report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from retail_forecast.features import feature_columns
from retail_forecast.monitoring import drift_report


if __name__ == "__main__":
    features = pd.read_csv("data/processed/features.csv")
    midpoint = len(features) // 2
    columns = feature_columns(features)[:10]
    report = drift_report(features.iloc[:midpoint], features.iloc[midpoint:], columns)
    report.to_csv("artifacts/drift_report.csv", index=False)
    print(report.to_string(index=False))
