"""Transaction to weekly category aggregation."""

from __future__ import annotations

import pandas as pd


def add_week_start(frame: pd.DataFrame, date_column: str = "transaction_date") -> pd.DataFrame:
    """Add Monday week_start based on a transaction date column."""
    result = frame.copy()
    dates = pd.to_datetime(result[date_column])
    result["week_start"] = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.normalize()
    return result


def aggregate_weekly_sales(transactions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transaction rows to store-category-week facts."""
    frame = add_week_start(transactions)
    grouped = (
        frame.groupby(["store_id", "category_id", "week_start"], as_index=False)
        .agg(
            sales_amount=("sales_amount", "sum"),
            sales_quantity=("sales_quantity", "sum"),
            is_promo_week=("is_promo", "max"),
            transactions_count=("transaction_id", "nunique"),
        )
        .sort_values(["store_id", "category_id", "week_start"])
    )
    grouped["sales_amount"] = grouped["sales_amount"].round(2)
    grouped["sales_quantity"] = grouped["sales_quantity"].round(3)
    grouped["is_promo_week"] = grouped["is_promo_week"].astype(bool)
    return grouped.reset_index(drop=True)
