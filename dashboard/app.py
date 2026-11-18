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
    sales_source = "X5 RetailHero" if summary.get("is_synthetic") is False else "синтетические продажи"
    promo_source = str(summary.get("promo_text_source", "не указан"))
    if promo_source.startswith("synthetic"):
        promo_label = "синтетические промо-тексты"
    elif promo_source == "provided_promo_texts":
        promo_label = "предоставленные промо-тексты"
    else:
        promo_label = promo_source
    return f"Продажи: {sales_source} · промо: {promo_label}"


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
    dependence = pd.read_csv(ROOT / "artifacts" / "feature_dependence.csv") if (ROOT / "artifacts" / "feature_dependence.csv").exists() else pd.DataFrame()
    explanations = pd.read_csv(ROOT / "artifacts" / "local_explanations.csv") if (ROOT / "artifacts" / "local_explanations.csv").exists() else pd.DataFrame()
    alerts = pd.read_csv(ROOT / "artifacts" / "monitoring_alerts.csv") if (ROOT / "artifacts" / "monitoring_alerts.csv").exists() else pd.DataFrame()
    summary = load_json("demo_summary.json")
    selected_store = st.sidebar.selectbox("Магазин", ["Все"] + sorted(weekly["store_id"].astype(str).unique().tolist()) if "store_id" in weekly else ["Все"])
    selected_category = st.sidebar.selectbox("Категория", ["Все"] + sorted(weekly["category_id"].astype(str).unique().tolist()) if "category_id" in weekly else ["Все"])
    weekly = _apply_filters(weekly, selected_store, selected_category)
    forecasts = _apply_filters(forecasts, selected_store, selected_category)

    if page == "Обзор":
        _overview(st, px, weekly, forecasts, summary)
    elif page == "Прогноз":
        _forecast(st, px, forecasts)
    elif page == "Качество модели":
        _model_quality(st, px, metrics, summary)
    elif page == "Качество данных":
        _data_quality(st, rejected, summary)
    elif page == "Мониторинг":
        _monitoring(st, px, drift, alerts, summary)
    else:
        _explainability(st, px, importance, dependence, explanations)


def _apply_filters(frame: pd.DataFrame, store: str, category: str) -> pd.DataFrame:
    result = frame.copy()
    if store != "Все" and "store_id" in result:
        result = result[result["store_id"].astype(str) == store]
    if category != "Все" and "category_id" in result:
        result = result[result["category_id"].astype(str) == category]
    return result


def _overview(st, px, weekly: pd.DataFrame, forecasts: pd.DataFrame, summary: dict[str, object]) -> None:
    if weekly.empty:
        st.warning("Нет подготовленных данных. Запустите make demo-local или make demo.")
        return
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    left, middle, right = st.columns(3)
    left.metric("Недельных строк", int(len(weekly)))
    middle.metric("Отклонено записей", int(summary.get("rejected_quality_rows", 0)))
    right.metric("Лучшая модель", str(summary.get("best_model", "нет")))
    recent_sales = float(weekly.sort_values("week_start").tail(4)["sales_amount"].sum())
    next_week = forecasts[forecasts["horizon"] == 1] if not forecasts.empty else pd.DataFrame()
    next_week_sales = float(next_week["forecast_value"].sum()) if not next_week.empty else 0.0
    quality = summary.get("best_metrics", {})
    left.metric("Продажи за последние 4 недели", f"{recent_sales:,.0f}")
    middle.metric("Прогноз на следующую неделю", f"{next_week_sales:,.0f}")
    right.metric("WAPE финального теста", f"{float(quality.get('WAPE', 0)):.1%}")
    sales = weekly.groupby("week_start", as_index=False)["sales_amount"].sum().rename(columns={"week_start": "week", "sales_amount": "value"})
    sales["series"] = "Факт"
    if not forecasts.empty:
        future = forecasts.groupby("target_week", as_index=False)["forecast_value"].sum().rename(columns={"target_week": "week", "forecast_value": "value"})
        future["series"] = "Прогноз"
        sales = pd.concat([sales, future], ignore_index=True)
    st.plotly_chart(px.line(sales, x="week", y="value", color="series", markers=True, title="Факт и прогноз продаж"), use_container_width=True)
    totals = weekly.groupby("category_id", as_index=False)["sales_amount"].sum().sort_values("sales_amount", ascending=False)
    st.plotly_chart(px.bar(totals, x="category_id", y="sales_amount", title="Продажи по категориям"), use_container_width=True)


def _forecast(st, px, forecasts: pd.DataFrame) -> None:
    if forecasts.empty:
        st.warning("Прогнозы еще не рассчитаны.")
        return
    horizons = sorted(forecasts["horizon"].dropna().astype(int).unique().tolist())
    selected_horizon = st.selectbox("Горизонт прогноза", horizons, index=0)
    forecasts = forecasts[forecasts["horizon"] == selected_horizon]
    st.dataframe(forecasts.sort_values(["target_week", "category_id", "store_id"]), use_container_width=True)
    st.download_button("Скачать прогноз CSV", forecasts.to_csv(index=False).encode("utf-8"), "forecasts.csv", "text/csv")
    st.plotly_chart(px.line(forecasts, x="target_week", y="forecast_value", color="horizon", title="Прогнозы на 1-4 недели"), use_container_width=True)


def _model_quality(st, px, metrics: pd.DataFrame, summary: dict[str, object]) -> None:
    if metrics.empty:
        st.warning("Метрики отсутствуют.")
        return
    selected_metric = st.selectbox("Метрика", sorted(metrics["metric_name"].unique().tolist()), index=sorted(metrics["metric_name"].unique().tolist()).index("WAPE") if "WAPE" in metrics["metric_name"].unique() else 0)
    shown = metrics[metrics["metric_name"] == selected_metric]
    st.dataframe(shown.pivot(index="model_name", columns="split_name", values="metric_value").reset_index(), use_container_width=True)
    st.plotly_chart(px.bar(shown, x="model_name", y="metric_value", color="split_name", barmode="group", title=f"Сравнение моделей по {selected_metric}"), use_container_width=True)
    st.caption("Модель выбрана по validation WAPE. Финальный тестовый период использован только для итоговой оценки.")
    st.json(summary.get("business_metrics", {}))


def _data_quality(st, rejected: pd.DataFrame, summary: dict[str, object]) -> None:
    st.metric("Отклоненные записи", int(summary.get("rejected_quality_rows", 0)))
    if rejected.empty:
        st.info("Отклоненные записи отсутствуют.")
    else:
        st.dataframe(rejected[[column for column in ["transaction_id", "issue_type"] if column in rejected]], use_container_width=True)
        st.bar_chart(rejected["issue_type"].value_counts())
    st.json(summary.get("flow_statuses", []))


def _monitoring(st, px, drift: pd.DataFrame, alerts: pd.DataFrame, summary: dict[str, object]) -> None:
    if not drift.empty:
        st.plotly_chart(px.bar(drift, x="feature", y="psi", title="PSI дрейф признаков"), use_container_width=True)
    if alerts.empty:
        st.info("Нет сохраненных оповещений мониторинга.")
        return
    st.dataframe(alerts.sort_values("severity"), use_container_width=True)
    if alerts["severity"].isin(["critical", "warning"]).any():
        st.warning("Проверьте причину сигнала. После анализа запустите make retrain, чтобы создать новую версию модели.")
    else:
        st.success("Критических отклонений не обнаружено.")


def _explainability(st, px, importance: pd.DataFrame, dependence: pd.DataFrame, explanations: pd.DataFrame) -> None:
    if importance.empty:
        st.warning("Важность признаков еще не рассчитана.")
        return
    chart = importance.sort_values("permutation_importance_validation", ascending=False).head(20)
    st.plotly_chart(px.bar(chart, x="permutation_importance_validation", y="feature", orientation="h", title="Permutation importance на validation"), use_container_width=True)
    st.dataframe(importance.head(20), use_container_width=True)
    if not dependence.empty:
        feature = st.selectbox("Зависимость прогноза от признака", sorted(dependence["feature"].unique().tolist()))
        selected = dependence[dependence["feature"] == feature]
        st.plotly_chart(px.line(selected, x="feature_value", y="mean_prediction", markers=True, title=f"Partial dependence: {feature}"), use_container_width=True)
    if not explanations.empty:
        st.subheader("Объяснение одного прогноза")
        st.caption(f"{explanations.iloc[0].get('store_id', '')} · {explanations.iloc[0].get('category_id', '')} · неделя {explanations.iloc[0].get('target_week', '')}")
        st.metric("Прогноз модели", f"{float(explanations.iloc[0]['prediction']):,.2f}", f"базовый уровень {float(explanations.iloc[0]['baseline_prediction']):,.2f}")
        st.plotly_chart(px.bar(explanations.head(15), x="contribution", y="feature", orientation="h", title="Вклад признаков в выбранный прогноз"), use_container_width=True)


if __name__ == "__main__":
    main()
