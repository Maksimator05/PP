"""Forecast quality metrics and business translation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def wape(y_true: pd.Series, y_pred: pd.Series) -> float:
    denominator = float(np.sum(np.abs(y_true)))
    return float(np.sum(np.abs(np.asarray(y_true) - np.asarray(y_pred))) / denominator) if denominator else 0.0


def smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    true = np.asarray(y_true)
    pred = np.asarray(y_pred)
    denominator = (np.abs(true) + np.abs(pred)) / 2
    values = np.divide(np.abs(true - pred), denominator, out=np.zeros_like(true, dtype=float), where=denominator != 0)
    return float(np.mean(values))


def evaluate(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    """Calculate standard regression metrics."""
    return {"MAE": mae(y_true, y_pred), "RMSE": rmse(y_true, y_pred), "WAPE": wape(y_true, y_pred), "sMAPE": smape(y_true, y_pred)}


def business_translation(metrics: dict[str, float], average_weekly_sales: float) -> str:
    """Translate metric values into category-management language."""
    lost_accuracy = metrics.get("WAPE", 0.0) * average_weekly_sales
    return f"Средняя относительная ошибка WAPE={metrics.get('WAPE', 0):.1%}; это около {lost_accuracy:,.0f} рублей недельного отклонения на типовую категорию."
