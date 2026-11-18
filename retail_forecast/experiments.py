"""Experiment logging with MLflow and a local fallback."""

from __future__ import annotations

import json
from pathlib import Path

from retail_forecast.models import ModelResult


def log_results(results: list[ModelResult], output_path: Path, run_metadata: dict[str, object] | None = None) -> Path:
    """Log metrics to MLflow when available and always write a JSON artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_metadata": run_metadata or {},
        "model_selection": "minimum validation WAPE",
        "models": {
            result.name: {
                "validation_metrics": result.validation_metrics,
                "test_metrics": result.metrics,
                "params": result.params,
                "feature_count": len(result.features),
                "train_seconds": result.train_seconds,
            }
            for result in results
        },
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import mlflow

        mlflow.set_experiment("retail_category_weekly_forecast")
        for result in results:
            with mlflow.start_run(run_name=result.name):
                mlflow.log_params({"model_name": result.name, "features_count": len(result.features), **result.params, **(run_metadata or {})})
                mlflow.log_metrics({f"validation_{key}": value for key, value in result.validation_metrics.items()})
                mlflow.log_metrics({f"test_{key}": value for key, value in result.metrics.items()})
    except Exception:
        pass
    return output_path
