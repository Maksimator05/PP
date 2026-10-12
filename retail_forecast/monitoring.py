"""Forecast quality and drift monitoring."""

from __future__ import annotations

import numpy as np
import pandas as pd

from retail_forecast.metrics import evaluate


def population_stability_index(expected, current, bins: int = 10) -> float:
    """PSI between two samples. Safe for boolean and numeric columns."""
    expected_values = (
        pd.to_numeric(pd.Series(expected).reset_index(drop=True), errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )
    current_values = (
        pd.to_numeric(pd.Series(current).reset_index(drop=True), errors="coerce")
        .dropna()
        .to_numpy(dtype=float)
    )
    if expected_values.size < 2 or current_values.size < 2:
        return 0.0

    breakpoints = np.quantile(expected_values, np.linspace(0, 1, bins + 1))
    breakpoints = np.unique(breakpoints)
    if breakpoints.size < 2:
        return 0.0

    expected_counts = np.histogram(expected_values, bins=breakpoints)[0] / float(expected_values.size)
    current_counts = np.histogram(current_values, bins=breakpoints)[0] / float(current_values.size)

    eps = 1e-4
    expected_counts = np.clip(expected_counts, eps, None)
    current_counts = np.clip(current_counts, eps, None)

    return float(np.sum((current_counts - expected_counts) * np.log(current_counts / expected_counts)))



def drift_report(reference: pd.DataFrame, current: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Build a PSI report for selected features."""
    return pd.DataFrame(
        [{"feature": column, "psi": population_stability_index(reference[column], current[column])} for column in columns if column in reference and column in current]
    )


def forecast_quality_report(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Calculate quality metrics for monitoring."""
    return evaluate(actual, predicted)
