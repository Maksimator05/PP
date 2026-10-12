"""Train models from processed features, creating them if needed."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from retail_forecast.features import build_features
from retail_forecast.models import save_model, select_best, train_all_models
from retail_forecast.splits import temporal_train_test_split


if __name__ == "__main__":
    weekly = pd.read_csv("data/processed/weekly_sales.csv")
    features = build_features(weekly)
    train, test = temporal_train_test_split(features)
    results = train_all_models(train, test)
    best = select_best(results)
    save_model(best, Path("models"))
    print(f"Best model: {best.name} metrics={best.metrics}")
