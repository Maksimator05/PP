from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.features import assert_no_target_leakage, build_features


def test_features_do_not_leak_future_target(small_transactions, small_promo_texts) -> None:
    weekly = aggregate_weekly_sales(small_transactions)
    features = build_features(weekly, small_promo_texts, lags=[1, 2], rolling_windows=[2], horizon=1)
    assert_no_target_leakage(features)
    assert (features["as_of_date"] < features["target_week"]).all()
