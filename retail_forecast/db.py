"""Database helpers for PostgreSQL or local SQLite fallback."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import uuid

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from retail_forecast.config import load_config


CORE_TABLES = [
    "x5_raw_transactions",
    "x5_raw_products",
    "x5_raw_stores",
    "x5_raw_promos",
    "sales_raw",
    "promo_texts_raw",
    "calendar_features",
    "pipeline_state",
    "etl_logs",
    "data_quality_issues",
    "feature_store",
    "forecasts",
    "metrics",
    "monitoring_alerts",
]


def get_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine."""
    config = load_config()
    url = database_url or config["database_url"]
    if url.startswith("sqlite"):
        Path("data/processed").mkdir(parents=True, exist_ok=True)
    return create_engine(url, future=True)


def init_database(engine: Engine, schema_path: Path) -> None:
    """Initialize database schema for PostgreSQL or the local SQL fallback."""
    statements = schema_path.read_text(encoding="utf-8").split(";") if schema_path.exists() else []
    with engine.begin() as connection:
        for statement in statements:
            sql = statement.strip()
            if sql:
                try:
                    connection.execute(text(sql))
                except Exception:
                    continue
        for table in CORE_TABLES:
            connection.execute(text(f'CREATE TABLE IF NOT EXISTS "{table}" (_row_id TEXT PRIMARY KEY, payload TEXT, created_at TEXT)'))


def upsert_like_replace(frame: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """Simple local persistence helper for demo and tests."""
    frame.to_sql(table_name, engine, if_exists="replace", index=False)


def write_table(frame: pd.DataFrame, table_name: str, engine: Engine, if_exists: str = "replace") -> int:
    """Write a dataframe to SQL and return the number of rows written."""
    frame.to_sql(table_name, engine, if_exists=if_exists, index=False)
    return int(len(frame))


def read_table(table_name: str, engine: Engine) -> pd.DataFrame:
    """Read a SQL table, returning an empty frame if the table is absent."""
    try:
        return pd.read_sql_table(table_name, engine)
    except Exception:
        return pd.DataFrame()


def row_counts(engine: Engine, tables: list[str] | None = None) -> dict[str, int]:
    """Return row counts for key tables."""
    tables = tables or CORE_TABLES
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in tables:
            try:
                counts[table] = int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)
            except Exception:
                counts[table] = 0
    return counts


def log_etl(engine: Engine, stage: str, status: str, rows_processed: int = 0, message: str = "") -> None:
    """Append an ETL log row."""
    frame = pd.DataFrame(
        [
            {
                "run_id": str(uuid.uuid4()),
                "stage": stage,
                "status": status,
                "rows_processed": rows_processed,
                "message": message,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    frame.to_sql("etl_logs", engine, if_exists="append", index=False)


def set_pipeline_state(engine: Engine, key: str, value: str, stage: str = "pipeline") -> None:
    """Upsert a simple pipeline state key/value."""
    current = read_table("pipeline_state", engine)
    row = pd.DataFrame([{"state_key": key, "state_value": value, "stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()}])
    if current.empty or "state_key" not in current:
        write_table(row, "pipeline_state", engine)
        return
    current = current[current["state_key"] != key]
    write_table(pd.concat([current, row], ignore_index=True), "pipeline_state", engine)
