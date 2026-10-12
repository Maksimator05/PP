"""Forecasting models, training and persistence."""

from __future__ import annotations

import pickle
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from retail_forecast.features import feature_columns
from retail_forecast.metrics import evaluate


class SeasonalNaiveRegressor:
    """Predict target as a configured historical lag."""

    def __init__(self, lag_column: str = "sales_amount_lag_4") -> None:
        self.lag_column = lag_column
        self.fallback_: float = 0.0

    def fit(self, x: pd.DataFrame, y: pd.Series) -> "SeasonalNaiveRegressor":
        self.fallback_ = float(y.mean()) if len(y) else 0.0
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        if self.lag_column in x:
            return x[self.lag_column].replace(0, self.fallback_).to_numpy(dtype=float)
        return np.repeat(self.fallback_, len(x))


@dataclass
class ModelResult:
    name: str
    model: Any
    metrics: dict[str, float]
    features: list[str]
    params: dict[str, Any]
    train_seconds: float
    validation_metrics: dict[str, float]


def make_catboost_or_fallback(random_seed: int = 42) -> Any:
    """Use CatBoost when installed; otherwise use a deterministic sklearn booster."""
    try:
        from catboost import CatBoostRegressor

        return CatBoostRegressor(iterations=80, depth=6, learning_rate=0.08, loss_function="RMSE", verbose=False, random_seed=random_seed)
    except Exception:
        return HistGradientBoostingRegressor(max_iter=100, learning_rate=0.08, random_state=random_seed)


def train_all_models(train: pd.DataFrame, test: pd.DataFrame, random_seed: int = 42, features: list[str] | None = None) -> list[ModelResult]:
    """Train baseline, linear and boosting models."""
    columns = features or feature_columns(train)
    x_train, y_train = train[columns], train["target_sales_amount"]
    x_test, y_test = test[columns], test["target_sales_amount"]
    models: dict[str, tuple[Any, dict[str, Any]]] = {
        "seasonal_naive": (SeasonalNaiveRegressor(), {"lag_column": "sales_amount_lag_4"}),
        "ridge": (Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=1.0))]), {"alpha": 1.0}),
        "catboost_or_histgb": (make_catboost_or_fallback(random_seed), {"iterations_or_max_iter": 80, "learning_rate": 0.08}),
        "random_forest_optional": (RandomForestRegressor(n_estimators=60, max_depth=8, random_state=random_seed, n_jobs=1), {"n_estimators": 60, "max_depth": 8}),
    }
    results: list[ModelResult] = []
    for name, (model, params) in models.items():
        started = time.perf_counter()
        model.fit(x_train, y_train)
        train_seconds = time.perf_counter() - started
        predictions = pd.Series(model.predict(x_test), index=test.index).clip(lower=0)
        metrics = evaluate(y_test, predictions)
        results.append(ModelResult(name=name, model=model, metrics=metrics, features=columns, params=params, train_seconds=train_seconds, validation_metrics=metrics))
    return results


def select_best(results: list[ModelResult], metric: str = "WAPE") -> ModelResult:
    """Select the model with the smallest error metric."""
    return min(results, key=lambda result: result.metrics[metric])


def save_model(result: ModelResult, output_dir: Path) -> Path:
    """Persist a trained model plus feature metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{result.name}.pkl"
    with path.open("wb") as file:
        pickle.dump({"model": result.model, "features": result.features, "metrics": result.metrics, "params": result.params}, file)
    latest = output_dir / "best_model.pkl"
    with latest.open("wb") as file:
        pickle.dump({"model": result.model, "features": result.features, "metrics": result.metrics, "params": result.params, "name": result.name}, file)
    return path


def feature_importance(result: ModelResult) -> pd.DataFrame:
    """Return feature importance or coefficient magnitude for interpretation."""
    model = result.model
    values: np.ndarray
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "named_steps") and "model" in model.named_steps and hasattr(model.named_steps["model"], "coef_"):
        values = np.abs(np.asarray(model.named_steps["model"].coef_, dtype=float))
    else:
        values = np.zeros(len(result.features), dtype=float)
    return pd.DataFrame({"feature": result.features, "importance": values}).sort_values("importance", ascending=False).head(50)
