from pathlib import Path

from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.features import build_features
from retail_forecast.models import save_model, select_best, train_all_models
from retail_forecast.splits import temporal_train_test_split


def test_models_train_predict_and_save(tmp_path: Path, small_transactions) -> None:
    features = build_features(aggregate_weekly_sales(small_transactions), lags=[1, 2, 3], rolling_windows=[2])
    train, test = temporal_train_test_split(features, test_weeks=4)
    results = train_all_models(train, test, random_seed=7)
    assert len(results) >= 3
    assert all(result.metrics["MAE"] >= 0 for result in results)
    path = save_model(select_best(results), tmp_path)
    assert path.exists()
