"""Time-series validation splits."""

from __future__ import annotations

import pandas as pd


def temporal_train_test_split(frame: pd.DataFrame, test_weeks: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use the last weeks as the final test period."""
    weeks = sorted(pd.to_datetime(frame["target_week"]).dropna().unique())
    if len(weeks) <= test_weeks:
        split_week = weeks[max(1, len(weeks) // 2)]
    else:
        split_week = weeks[-test_weeks]
    train = frame[pd.to_datetime(frame["target_week"]) < split_week].copy()
    test = frame[pd.to_datetime(frame["target_week"]) >= split_week].copy()
    return train, test


def temporal_train_validation_test_split(
    frame: pd.DataFrame,
    validation_weeks: int = 8,
    test_weeks: int = 8,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reserve the latest period as an untouched final test after validation."""
    weeks = sorted(pd.to_datetime(frame["target_week"]).dropna().unique())
    if len(weeks) < 3:
        raise ValueError("At least three distinct target weeks are required for train/validation/test splitting")
    test_count = min(test_weeks, max(1, len(weeks) // 4))
    validation_count = min(validation_weeks, max(1, (len(weeks) - test_count) // 4))
    test_start = weeks[-test_count]
    validation_end = test_start
    validation_start = weeks[max(1, len(weeks) - test_count - validation_count)]
    train = frame[pd.to_datetime(frame["target_week"]) < validation_start].copy()
    validation = frame[(pd.to_datetime(frame["target_week"]) >= validation_start) & (pd.to_datetime(frame["target_week"]) < validation_end)].copy()
    test = frame[pd.to_datetime(frame["target_week"]) >= test_start].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("Unable to create non-empty chronological train, validation and test periods")
    return train, validation, test


def rolling_splits(frame: pd.DataFrame, n_splits: int = 3, validation_weeks: int = 4, embargo_weeks: int = 1) -> list[tuple[pd.Index, pd.Index]]:
    """Create expanding-window splits with an embargo before validation."""
    weeks = sorted(pd.to_datetime(frame["target_week"]).dropna().unique())
    splits: list[tuple[pd.Index, pd.Index]] = []
    min_train = max(4, len(weeks) - n_splits * validation_weeks - embargo_weeks)
    for split_number in range(n_splits):
        val_start_idx = min_train + split_number * validation_weeks + embargo_weeks
        val_end_idx = min(val_start_idx + validation_weeks, len(weeks))
        if val_start_idx >= len(weeks):
            break
        train_weeks = weeks[: max(0, val_start_idx - embargo_weeks)]
        val_weeks = weeks[val_start_idx:val_end_idx]
        train_idx = frame.index[pd.to_datetime(frame["target_week"]).isin(train_weeks)]
        val_idx = frame.index[pd.to_datetime(frame["target_week"]).isin(val_weeks)]
        if len(train_idx) and len(val_idx):
            splits.append((train_idx, val_idx))
    return splits
