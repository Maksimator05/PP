import pandas as pd

from retail_forecast.aggregation import aggregate_weekly_sales


def test_weekly_aggregation_monday_start(small_transactions: pd.DataFrame) -> None:
    weekly = aggregate_weekly_sales(small_transactions)
    assert not weekly.duplicated(["store_id", "category_id", "week_start"]).any()
    assert set(pd.to_datetime(weekly["week_start"]).dt.weekday.unique()) == {0}
    assert round(weekly["sales_amount"].sum(), 2) == round(small_transactions["sales_amount"].sum(), 2)
