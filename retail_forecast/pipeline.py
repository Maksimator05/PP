"""End-to-end pipelines for local SQL and PostgreSQL-backed demos."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from retail_forecast.aggregation import aggregate_weekly_sales
from retail_forecast.config import PROJECT_ROOT, load_config, project_path
from retail_forecast.db import get_engine, init_database, log_etl, read_table, row_counts, set_pipeline_state, write_table
from retail_forecast.downloader import ensure_dataset, verify_x5_dataset
from retail_forecast.experiments import log_results
from retail_forecast.features import build_features, feature_columns, select_features
from retail_forecast.logging_utils import setup_logger
from retail_forecast.metrics import evaluate
from retail_forecast.models import feature_importance, save_model, select_best, train_all_models
from retail_forecast.monitoring import drift_report
from retail_forecast.quality import inject_bad_records, validate_transactions
from retail_forecast.splits import temporal_train_test_split
from retail_forecast.x5_loader import load_transactions, profile_dataset


KEY_TABLES = [
    "sales_raw",
    "promo_texts_raw",
    "feature_store",
    "forecasts",
    "metrics",
    "etl_logs",
    "data_quality_issues",
    "monitoring_alerts",
]


def run_demo(database_url: str | None = None, demonstrate_quality: bool = True) -> dict[str, object]:
    """Run the complete local SQL demonstration pipeline."""
    logger = setup_logger("retail_forecast.pipeline", "etl.log")
    config = load_config()
    engine = get_engine(database_url)
    init_database(engine, PROJECT_ROOT / "sql" / "001_schema.sql")
    output = project_path(config["data"]["processed_path"])
    output.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "artifacts").mkdir(exist_ok=True)
    run_id = str(uuid.uuid4())

    status = ensure_dataset(force=False)
    log_etl(engine, "download_x5_dataset_flow", "success", status.rows, status.message)
    transactions = load_transactions(status.path)
    if demonstrate_quality:
        transactions_for_quality = inject_bad_records(transactions)
    else:
        transactions_for_quality = transactions
    valid, rejected = validate_transactions(transactions_for_quality)
    valid = valid.drop_duplicates(subset=["transaction_id"]).copy()
    valid["source_name"] = status.source
    write_table(valid, "x5_raw_transactions", engine)
    log_etl(engine, "ingest_x5_raw_flow", "success", len(valid), "raw transactions loaded")

    quality_rows = _quality_issues(rejected)
    write_table(quality_rows, "data_quality_issues", engine)
    weekly = aggregate_weekly_sales(valid)
    weekly["source_batch_id"] = run_id
    previous_state = read_table("pipeline_state", engine)
    previous_week = _state_value(previous_state, "last_processed_week")
    new_week_rows = len(weekly) if not previous_week else int((pd.to_datetime(weekly["week_start"]) > pd.Timestamp(previous_week)).sum())
    write_table(weekly, "sales_raw", engine)
    set_pipeline_state(engine, "last_processed_week", str(pd.to_datetime(weekly["week_start"]).max().date()), "ingest_sales_flow")
    log_etl(engine, "ingest_sales_flow", "success", new_week_rows, "new weekly rows loaded" if new_week_rows else "новых данных нет")

    promo_path = status.path / "promo_texts.csv"
    promo = pd.read_csv(promo_path) if promo_path.exists() else pd.DataFrame()
    if not promo.empty:
        promo["week_start"] = pd.to_datetime(promo["week_start"])
    write_table(promo, "promo_texts_raw", engine)
    log_etl(engine, "ingest_promo_flow", "success", len(promo), "promo texts loaded")

    calendar = _calendar_features(weekly)
    write_table(calendar, "calendar_features", engine)
    log_etl(engine, "build_calendar_flow", "success", len(calendar), "calendar features built")

    features = build_features(
        weekly,
        promo,
        lags=config["forecast"]["lags"],
        rolling_windows=config["forecast"]["rolling_windows"],
        horizon=int(config["forecast"]["horizon_weeks"]),
    )
    selected, selection_report = select_features(features)
    write_table(features, "feature_store", engine)
    (PROJECT_ROOT / "artifacts" / "selected_features.json").write_text(json.dumps({"selected_features": selected, **selection_report}, ensure_ascii=False, indent=2), encoding="utf-8")
    log_etl(engine, "build_features_flow", "success", len(features), f"features selected: {selection_report}")

    train, test = temporal_train_test_split(features, test_weeks=8)
    results = train_all_models(train, test, random_seed=int(config["project"]["random_seed"]), features=selected)
    best = select_best(results)
    model_path = save_model(best, PROJECT_ROOT / "models")
    metrics_path = log_results(results, PROJECT_ROOT / "artifacts" / "model_metrics.json")
    metrics_frame = _metrics_frame(run_id, results)
    write_table(metrics_frame, "metrics", engine)
    log_etl(engine, "train_models_flow", "success", len(results), f"best_model={best.name}")

    forecasts = _make_forecasts(best, features, weekly, horizons=[1, 2, 3, 4])
    write_table(forecasts, "forecasts", engine)
    log_etl(engine, "inference_flow", "success", len(forecasts), "forecasts for horizons 1-4 saved")

    predictions = pd.Series(best.model.predict(test[best.features]), index=test.index).clip(lower=0)
    business_metrics = _business_metrics(test["target_sales_amount"], predictions)
    (PROJECT_ROOT / "artifacts" / "business_metrics.json").write_text(json.dumps(business_metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    importance = feature_importance(best)
    write_table(importance, "feature_importance", engine)
    importance.to_csv(PROJECT_ROOT / "artifacts" / "feature_importance.csv", index=False)
    _local_explanations(best, features, forecasts).to_csv(PROJECT_ROOT / "artifacts" / "local_explanations.csv", index=False)

    drift = _monitoring(engine, features, selected, best.metrics.get("WAPE", 0.0))
    log_etl(engine, "monitoring_flow", "success", len(drift), "monitoring completed")

    valid.to_csv(output / "transactions_valid.csv", index=False)
    rejected.to_csv(output / "transactions_rejected.csv", index=False)
    weekly.to_csv(output / "weekly_sales.csv", index=False)
    features.to_csv(output / "features.csv", index=False)
    forecasts.to_csv(output / "forecasts.csv", index=False)
    metrics_frame.to_csv(output / "metrics.csv", index=False)
    row_count_report = row_counts(engine, KEY_TABLES)
    (PROJECT_ROOT / "artifacts" / "db_row_counts.json").write_text(json.dumps(row_count_report, ensure_ascii=False, indent=2), encoding="utf-8")
    profile = profile_dataset(valid)
    (PROJECT_ROOT / "docs" / "x5_dataset_profile.md").write_text(_profile_markdown(profile, status.source), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "database_url": str(engine.url),
        "dataset_source": status.source,
        "is_synthetic": status.is_synthetic,
        "transactions": len(transactions),
        "rejected_quality_rows": len(rejected),
        "weekly_rows": len(weekly),
        "new_week_rows": new_week_rows,
        "features_rows": len(features),
        "features_before": selection_report["features_before"],
        "features_after": selection_report["features_after"],
        "best_model": best.name,
        "best_metrics": best.metrics,
        "business_metrics": business_metrics,
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "row_counts": row_count_report,
        "flow_statuses": _flow_statuses(engine),
    }
    (PROJECT_ROOT / "artifacts" / "demo_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    logger.info("Demo completed: %s", summary)
    return summary


def inspect_x5() -> dict[str, object]:
    """Verify local X5 and write a profile."""
    status = verify_x5_dataset()
    transactions = load_transactions(status.path)
    profile = profile_dataset(transactions)
    (PROJECT_ROOT / "docs" / "x5_dataset_profile.md").write_text(_profile_markdown(profile, status.source), encoding="utf-8")
    return {"status": status.message, "rows": status.rows, "path": str(status.path), "profile": profile}


def _quality_issues(rejected: pd.DataFrame) -> pd.DataFrame:
    if rejected.empty:
        return pd.DataFrame(columns=["issue_id", "issue_type", "severity", "transaction_id", "message", "created_at"])
    return pd.DataFrame(
        {
            "issue_id": rejected["issue_id"],
            "issue_type": rejected["issue_type"],
            "severity": "error",
            "transaction_id": rejected["transaction_id"].astype(str),
            "message": "Rejected by data quality validator",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _calendar_features(weekly: pd.DataFrame) -> pd.DataFrame:
    weeks = pd.DataFrame({"week_start": sorted(pd.to_datetime(weekly["week_start"]).unique())})
    weeks["weekofyear"] = weeks["week_start"].dt.isocalendar().week.astype(int)
    weeks["month"] = weeks["week_start"].dt.month
    weeks["quarter"] = weeks["week_start"].dt.quarter
    weeks["is_holiday"] = weeks["week_start"].dt.strftime("%m-%d").isin({"01-01", "01-07", "02-23", "03-08", "05-01", "05-09", "06-12", "11-04"})
    return weeks


def _metrics_frame(run_id: str, results) -> pd.DataFrame:
    rows = []
    for result in results:
        for metric, value in result.metrics.items():
            rows.append(
                {
                    "run_id": run_id,
                    "model_name": result.name,
                    "split_name": "final_test",
                    "metric_name": metric,
                    "metric_value": value,
                    "params_json": json.dumps(result.params, ensure_ascii=False),
                    "train_seconds": result.train_seconds,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    return pd.DataFrame(rows)


def _make_forecasts(best, features: pd.DataFrame, weekly: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    latest = features.sort_values("week_start").groupby(["store_id", "category_id"], as_index=False).tail(1).copy()
    base_pred = pd.Series(best.model.predict(latest[best.features]), index=latest.index).clip(lower=0)
    residual_width = max(float(best.metrics.get("MAE", 0.0)), 1.0)
    max_week = pd.to_datetime(weekly["week_start"]).max()
    rows = []
    for horizon in horizons:
        for idx, row in latest.iterrows():
            value = float(base_pred.loc[idx])
            target_week = max_week + pd.Timedelta(weeks=horizon)
            rows.append(
                {
                    "model_name": best.name,
                    "model_version": "local_best",
                    "store_id": row["store_id"],
                    "category_id": row["category_id"],
                    "target_week": target_week.date().isoformat(),
                    "horizon": horizon,
                    "forecast_value": round(value, 2),
                    "lower_bound": round(max(0.0, value - 1.96 * residual_width), 2),
                    "upper_bound": round(value + 1.96 * residual_width, 2),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    return pd.DataFrame(rows)


def _business_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    errors = predicted - actual
    relative = (errors.abs() / actual.abs().replace(0, pd.NA)).fillna(0)
    return {
        "average_error_rub": float(errors.abs().mean()),
        "total_absolute_error_rub": float(errors.abs().sum()),
        "share_forecasts_error_gt_20pct": float((relative > 0.20).mean()),
        "strong_underforecast_weeks": int((errors < -0.20 * actual).sum()),
        "strong_overforecast_weeks": int((errors > 0.20 * actual).sum()),
        "understock_risk_rub": float((-errors[errors < 0]).sum()),
        "overstock_risk_rub": float(errors[errors > 0].sum()),
    }


def _monitoring(engine, features: pd.DataFrame, selected: list[str], best_wape: float) -> pd.DataFrame:
    midpoint = len(features) // 2
    drift = drift_report(features.iloc[:midpoint], features.iloc[midpoint:], selected[:20])
    drift.to_csv(PROJECT_ROOT / "artifacts" / "drift_report.csv", index=False)
    alerts = []
    for row in drift.itertuples(index=False):
        if row.psi > 0.25:
            alerts.append(_alert("feature_drift", "critical", row.feature, f"Feature drift PSI={row.psi:.3f}", float(row.psi), 0.25))
        elif row.psi > 0.10:
            alerts.append(_alert("feature_drift", "warning", row.feature, f"Feature drift PSI={row.psi:.3f}", float(row.psi), 0.10))
    if best_wape > 0.40:
        alerts.append(_alert("quality_drop", "critical", "best_model", "WAPE is above critical threshold; retraining recommended", best_wape, 0.40))
    elif best_wape > 0.25:
        alerts.append(_alert("quality_drop", "warning", "best_model", "WAPE is above warning threshold; monitor and consider retraining", best_wape, 0.25))
    if not alerts:
        alerts.append(_alert("monitoring_ok", "info", "system", "No active critical alerts", 0.0, 0.0))
    alert_frame = pd.DataFrame(alerts)
    write_table(alert_frame, "monitoring_alerts", engine)
    return drift


def _alert(alert_type: str, severity: str, entity_id: str, message: str, metric_value: float, threshold_value: float) -> dict[str, object]:
    return {
        "alert_id": str(uuid.uuid4()),
        "alert_type": alert_type,
        "severity": severity,
        "entity_id": entity_id,
        "message": message,
        "metric_value": metric_value,
        "threshold_value": threshold_value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _local_explanations(best, features: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    importance = feature_importance(best).head(10)
    sample = forecasts.head(20)[["store_id", "category_id", "target_week", "horizon"]].copy()
    sample["top_features"] = ", ".join(importance["feature"].tolist())
    sample["explanation"] = "Локальное объяснение построено через глобальную важность признаков fallback."
    return sample


def _state_value(state: pd.DataFrame, key: str) -> str | None:
    if state.empty or "state_key" not in state:
        return None
    matched = state[state["state_key"] == key]
    if matched.empty:
        return None
    return str(matched.iloc[0]["state_value"])


def _flow_statuses(engine) -> list[dict[str, object]]:
    logs = read_table("etl_logs", engine)
    if logs.empty:
        return []
    return logs[["stage", "status", "rows_processed", "message", "created_at"]].tail(20).to_dict(orient="records")


def _profile_markdown(profile: dict[str, object], source: str) -> str:
    missing = profile.get("missing", {})
    missing_lines = "\n".join(f"- `{key}`: {value}" for key, value in dict(missing).items())
    source_label = "X5 RetailHero" if "x5" in source and "synthetic" not in source else "synthetic fallback (X5 недоступен в текущей среде)"
    return (
        "# Профиль датасета X5 RetailHero\n\n"
        f"- Источник: {source_label}\n"
        f"- Технический код источника: `{source}`\n"
        f"- Строк: {profile.get('rows')}\n"
        f"- Колонки: {', '.join(profile.get('columns', []))}\n"
        f"- Дубликаты: {profile.get('duplicates')}\n"
        f"- Диапазон дат: {profile.get('date_min')} - {profile.get('date_max')}\n\n"
        "## Пропуски\n\n"
        f"{missing_lines}\n"
    )
