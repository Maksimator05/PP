"""Experiment logging with MLflow and a local fallback."""

from __future__ import annotations

import json
from pathlib import Path

from retail_forecast.models import ModelResult


def log_results(results: list[ModelResult], output_path: Path) -> Path:
    """Log metrics to MLflow when available and always write a JSON artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {result.name: result.metrics for result in results}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import mlflow

        mlflow.set_experiment("retail_category_weekly_forecast")
        for result in results:
            with mlflow.start_run(run_name=result.name):
                mlflow.log_params({"model_name": result.name, "features_count": len(result.features)})
                mlflow.log_metrics(result.metrics)
    except Exception:
        pass
    return output_path
