"""Leakage-safe feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd

from retail_forecast.text_features import build_text_features


def build_features(
    weekly_sales: pd.DataFrame,
    promo_texts: pd.DataFrame | None = None,
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
    horizon: int = 1,
) -> pd.DataFrame:
    """Build supervised features using only information available before target week."""
    lags = lags or [1, 2, 3, 4, 8, 12, 52]
    rolling_windows = rolling_windows or [4, 8, 12]
    frame = weekly_sales.copy()
    frame["week_start"] = pd.to_datetime(frame["week_start"])
    frame = frame.sort_values(["store_id", "category_id", "week_start"]).reset_index(drop=True)
    group = frame.groupby(["store_id", "category_id"], group_keys=False)

    for lag in lags:
        frame[f"sales_amount_lag_{lag}"] = group["sales_amount"].shift(lag)
        frame[f"sales_quantity_lag_{lag}"] = group["sales_quantity"].shift(lag)

    for window in rolling_windows:
        shifted = group["sales_amount"].shift(1)
        frame[f"sales_amount_roll_mean_{window}"] = shifted.groupby([frame["store_id"], frame["category_id"]]).rolling(window).mean().reset_index(level=[0, 1], drop=True)
        frame[f"sales_amount_roll_std_{window}"] = shifted.groupby([frame["store_id"], frame["category_id"]]).rolling(window).std().reset_index(level=[0, 1], drop=True)
        frame[f"sales_amount_ewma_{window}"] = shifted.groupby([frame["store_id"], frame["category_id"]]).transform(lambda values: values.ewm(span=window, adjust=False).mean())

    frame["target_week"] = group["week_start"].shift(-horizon)
    frame["target_sales_amount"] = group["sales_amount"].shift(-horizon)
    frame["as_of_date"] = frame["week_start"]
    frame["weekofyear"] = frame["target_week"].dt.isocalendar().week.astype("float")
    frame["month"] = frame["target_week"].dt.month
    frame["quarter"] = frame["target_week"].dt.quarter
    frame["is_holiday"] = frame["target_week"].dt.strftime("%m-%d").isin({"01-01", "01-07", "02-23", "03-08", "05-01", "05-09", "06-12", "11-04"}).astype(int)
    frame["store_code"] = frame["store_id"].astype("category").cat.codes
    frame["category_code"] = frame["category_id"].astype("category").cat.codes
    frame["promo_x_holiday"] = frame["is_promo_week"].astype(int) * frame["is_holiday"]
    frame["category_x_month"] = frame["category_code"] * frame["month"]

    if promo_texts is not None and not promo_texts.empty:
        text_features = build_text_features(promo_texts)
        frame = frame.merge(text_features, on=["store_id", "category_id", "week_start"], how="left")

    numeric_columns = frame.select_dtypes(include=["number", "bool"]).columns
    frame[numeric_columns] = frame[numeric_columns].fillna(0)
    frame = frame.dropna(subset=["target_week", "target_sales_amount"])
    assert_no_target_leakage(frame)
    return frame.reset_index(drop=True)


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return model feature columns."""
    excluded = {
        "sales_amount",
        "sales_quantity",
        "transactions_count",
        "target_sales_amount",
        "week_start",
        "target_week",
        "as_of_date",
        "store_id",
        "category_id",
    }
    return [column for column in frame.columns if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])]


def assert_no_target_leakage(frame: pd.DataFrame) -> None:
    """Validate that features are cut before the target week."""
    invalid = pd.to_datetime(frame["as_of_date"]) >= pd.to_datetime(frame["target_week"])
    if invalid.any():
        raise ValueError("Feature leakage detected: as_of_date must be earlier than target_week")
    forbidden = {"target_sales_amount"}
    leakage_columns = forbidden.intersection(feature_columns(frame))
    if leakage_columns:
        raise ValueError(f"Feature leakage detected in columns: {sorted(leakage_columns)}")


def select_features(frame: pd.DataFrame, correlation_threshold: float = 0.98) -> tuple[list[str], dict[str, object]]:
    """Drop constant and highly correlated numeric features."""
    candidates = feature_columns(frame)
    selected = [column for column in candidates if frame[column].nunique(dropna=False) > 1]
    dropped_corr: list[str] = []
    if selected:
        corr = frame[selected].corr(numeric_only=True).abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        dropped_corr = [column for column in upper.columns if bool((upper[column] > correlation_threshold).any())]
        selected = [column for column in selected if column not in dropped_corr]
    report = {"features_before": len(candidates), "features_after": len(selected), "dropped_correlated": dropped_corr}
    return selected, report
