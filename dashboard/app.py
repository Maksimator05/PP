"""Decision dashboard backed by prepared SQL/CSV artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_csv(name: str) -> pd.DataFrame:
    """Load a prepared artifact without breaking dashboard imports."""
    path = Path(name)
    if not path.is_absolute():
        path = ROOT / "data" / "processed" / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def load_json(name: str) -> dict[str, object]:
    path = ROOT / "artifacts" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def data_source_label() -> str:
    summary = load_json("demo_summary.json")
    return "Источник: X5 RetailHero" if summary.get("is_synthetic") is False else "Источник: synthetic fallback (X5 недоступен в текущей среде)"


def available_pages() -> list[str]:
    return ["Обзор", "Прогноз", "Качество модели", "Качество данных", "Мониторинг", "Объяснимость"]


def main() -> None:
    import plotly.express as px
    import streamlit as st

    st.set_page_config(page_title="Прогноз недельных продаж", layout="wide")
    st.title("Прогноз недельных продаж по категориям")
    st.caption(data_source_label())
    page = st.sidebar.radio("Раздел", available_pages())
    weekly = load_csv("weekly_sales.csv")
    forecasts = load_csv("forecasts.csv")
    metrics = load_csv("metrics.csv")
    rejected = load_csv("transactions_rejected.csv")
    drift = pd.read_csv(ROOT / "artifacts" / "drift_report.csv") if (ROOT / "artifacts" / "drift_report.csv").exists() else pd.DataFrame()
    importance = pd.read_csv(ROOT / "artifacts" / "feature_importance.csv") if (ROOT / "artifacts" / "feature_importance.csv").exists() else pd.DataFrame()
    summary = load_json("demo_summary.json")

    if page == "Обзор":
        _overview(st, px, weekly, summary)
    elif page == "Прогноз":
        _forecast(st, px, forecasts)
    elif page == "Качество модели":
        _model_quality(st, px, metrics, summary)
    elif page == "Качество данных":
        _data_quality(st, rejected, summary)
    elif page == "Мониторинг":
        _monitoring(st, px, drift, summary)
    else:
        _explainability(st, px, importance)


def _overview(st, px, weekly: pd.DataFrame, summary: dict[str, object]) -> None:
    if weekly.empty:
        st.warning("Нет подготовленных данных. Запустите make demo-local или make demo.")
        return
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    left, middle, right = st.columns(3)
    left.metric("Недельных строк", int(len(weekly)))
    middle.metric("Отклонено записей", int(summary.get("rejected_quality_rows", 0)))
    right.metric("Лучшая модель", str(summary.get("best_model", "нет")))
    sales = weekly.groupby("week_start", as_index=False)["sales_amount"].sum()
    st.plotly_chart(px.line(sales, x="week_start", y="sales_amount", title="Фактические продажи"), use_container_width=True)
    totals = weekly.groupby("category_id", as_index=False)["sales_amount"].sum().sort_values("sales_amount", ascending=False)
    st.plotly_chart(px.bar(totals, x="category_id", y="sales_amount", title="Продажи по категориям"), use_container_width=True)


def _forecast(st, px, forecasts: pd.DataFrame) -> None:
    if forecasts.empty:
        st.warning("Прогнозы еще не рассчитаны.")
        return
    st.dataframe(forecasts, use_container_width=True)
    st.download_button("Скачать прогноз CSV", forecasts.to_csv(index=False).encode("utf-8"), "forecasts.csv", "text/csv")
    st.plotly_chart(px.line(forecasts, x="target_week", y="forecast_value", color="horizon", title="Прогнозы на 1-4 недели"), use_container_width=True)


def _model_quality(st, px, metrics: pd.DataFrame, summary: dict[str, object]) -> None:
    if metrics.empty:
        st.warning("Метрики отсутствуют.")
        return
    st.dataframe(metrics, use_container_width=True)
    st.plotly_chart(px.bar(metrics, x="model_name", y="metric_value", color="metric_name", barmode="group", title="Сравнение моделей"), use_container_width=True)
    st.json(summary.get("business_metrics", {}))


def _data_quality(st, rejected: pd.DataFrame, summary: dict[str, object]) -> None:
    st.metric("Отклоненные записи", int(summary.get("rejected_quality_rows", 0)))
    if rejected.empty:
        st.info("Отклоненные записи отсутствуют.")
    else:
        st.dataframe(rejected[[column for column in ["transaction_id", "issue_type"] if column in rejected]], use_container_width=True)
        st.bar_chart(rejected["issue_type"].value_counts())
    st.json(summary.get("flow_statuses", []))


def _monitoring(st, px, drift: pd.DataFrame, summary: dict[str, object]) -> None:
    if not drift.empty:
        st.plotly_chart(px.bar(drift, x="feature", y="psi", title="PSI дрейф признаков"), use_container_width=True)
    st.json({"active_alerts": summary.get("row_counts", {}).get("monitoring_alerts", 0), "recommendation": "При критическом WAPE или PSI выполните make retrain."})


def _explainability(st, px, importance: pd.DataFrame) -> None:
    if importance.empty:
        st.warning("Важность признаков еще не рассчитана.")
        return
    st.plotly_chart(px.bar(importance.head(20), x="importance", y="feature", orientation="h", title="Топ-20 важных признаков"), use_container_width=True)
    local_path = ROOT / "artifacts" / "local_explanations.csv"
    if local_path.exists():
        st.dataframe(pd.read_csv(local_path), use_container_width=True)


if __name__ == "__main__":
    main()
