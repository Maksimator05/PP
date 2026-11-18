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

    if np.ptp(expected_values) == 0:
        center = expected_values[0]
        cuts = np.array([center - 1e-9, center + 1e-9])
    else:
        cuts = np.unique(np.quantile(expected_values, np.linspace(0, 1, bins + 1)[1:-1]))
        if cuts.size == 0:
            cuts = np.array([float(np.min(expected_values)), float(np.max(expected_values))])

    # Digitizing with internal cut points keeps values beyond the reference range
    # in underflow/overflow bins instead of silently dropping them.
    n_bins = len(cuts) + 1
    expected_counts = np.bincount(np.digitize(expected_values, cuts), minlength=n_bins).astype(float) / float(expected_values.size)
    current_counts = np.bincount(np.digitize(current_values, cuts), minlength=n_bins).astype(float) / float(current_values.size)

    eps = 1e-4
    expected_counts = np.clip(expected_counts, eps, None)
    current_counts = np.clip(current_counts, eps, None)
    expected_counts /= expected_counts.sum()
    current_counts /= current_counts.sum()

    return float(np.sum((current_counts - expected_counts) * np.log(current_counts / expected_counts)))



def drift_report(reference: pd.DataFrame, current: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Build a PSI report for selected features."""
    return pd.DataFrame(
        [{"feature": column, "psi": population_stability_index(reference[column], current[column])} for column in columns if column in reference and column in current]
    )


def forecast_quality_report(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Calculate quality metrics for monitoring."""
    return evaluate(actual, predicted)
