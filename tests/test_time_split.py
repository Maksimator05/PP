from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.features import build_features
from retail_forecast.splits import rolling_splits, temporal_train_test_split


def test_temporal_split_orders_train_before_test(small_transactions) -> None:
    features = build_features(aggregate_weekly_sales(small_transactions), lags=[1], rolling_windows=[2])
    train, test = temporal_train_test_split(features, test_weeks=4)
    assert train["target_week"].max() < test["target_week"].min()


def test_rolling_split_has_no_overlap_and_embargo(small_transactions) -> None:
    features = build_features(aggregate_weekly_sales(small_transactions), lags=[1], rolling_windows=[2])
    splits = rolling_splits(features, n_splits=2, validation_weeks=2, embargo_weeks=1)
    assert splits
    for train_idx, val_idx in splits:
        assert set(train_idx).isdisjoint(set(val_idx))
        assert features.loc[train_idx, "target_week"].max() < features.loc[val_idx, "target_week"].min()
