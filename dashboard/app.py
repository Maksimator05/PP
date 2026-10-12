"""Streamlit dashboard for category sales forecasts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_weekly(path: str = "data/processed/weekly_sales.csv") -> pd.DataFrame:
    """Load weekly sales for the dashboard."""
    file = Path(path)
    if not file.exists():
        return pd.DataFrame(columns=["store_id", "category_id", "week_start", "sales_amount", "sales_quantity", "is_promo_week"])
    frame = pd.read_csv(file)
    frame["week_start"] = pd.to_datetime(frame["week_start"])
    return frame


def main() -> None:
    import streamlit as st
    import plotly.express as px

    st.set_page_config(page_title="Прогноз недельных продаж", layout="wide")
    st.title("Прогноз недельных продаж по категориям")
    weekly = load_weekly()
    if weekly.empty:
        st.warning("Данные не найдены. Запустите `make demo`.")
        return

    stores = sorted(weekly["store_id"].unique())
    categories = sorted(weekly["category_id"].unique())
    left, right = st.columns(2)
    store = left.selectbox("Магазин", stores)
    category = right.selectbox("Категория", categories)
    filtered = weekly[(weekly["store_id"] == store) & (weekly["category_id"] == category)]
    st.metric("Недельная выручка, средняя", f"{filtered['sales_amount'].mean():,.0f}")
    st.metric("Промо-недель", int(filtered["is_promo_week"].sum()))
    st.plotly_chart(px.line(filtered, x="week_start", y="sales_amount", title="Фактические недельные продажи"), use_container_width=True)
    st.plotly_chart(px.bar(weekly.groupby("category_id", as_index=False)["sales_amount"].sum(), x="category_id", y="sales_amount", title="Продажи по категориям"), use_container_width=True)
    metrics_path = Path("artifacts/model_metrics.json")
    if metrics_path.exists():
        st.subheader("Метрики моделей")
        st.json(metrics_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
