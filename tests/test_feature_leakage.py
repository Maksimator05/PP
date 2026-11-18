from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.features import assert_no_target_leakage, build_features
from retail_forecast.features import feature_columns


def test_features_do_not_leak_future_target(small_transactions, small_promo_texts) -> None:
    weekly = aggregate_weekly_sales(small_transactions)
    features = build_features(weekly, small_promo_texts, lags=[1, 2], rolling_windows=[2], horizon=1)
    assert_no_target_leakage(features)
    assert (features["as_of_date"] < features["target_week"]).all()


def test_future_sales_mutation_does_not_change_same_week_input_features(small_transactions, small_promo_texts) -> None:
    weekly = aggregate_weekly_sales(small_transactions)
    features = build_features(weekly, small_promo_texts, lags=[1, 2], rolling_windows=[2], horizon=1)
    series = weekly[(weekly["store_id"] == "store_01") & (weekly["category_id"] == "cat_01")].sort_values("week_start")
    changed_week = series.iloc[8]["week_start"]
    mutated = weekly.copy()
    mask = (mutated["store_id"] == "store_01") & (mutated["category_id"] == "cat_01") & (mutated["week_start"] == changed_week)
    mutated.loc[mask, "sales_amount"] *= 10
    changed_features = build_features(mutated, small_promo_texts, lags=[1, 2], rolling_windows=[2], horizon=1)

    key = ("store_01", "cat_01", changed_week)
    original_row = features[(features["store_id"] == key[0]) & (features["category_id"] == key[1]) & (features["target_week"] == key[2])].iloc[0]
    changed_row = changed_features[(changed_features["store_id"] == key[0]) & (changed_features["category_id"] == key[1]) & (changed_features["target_week"] == key[2])].iloc[0]
    assert original_row["target_sales_amount"] != changed_row["target_sales_amount"]
    assert original_row[feature_columns(features)].equals(changed_row[feature_columns(changed_features)])
