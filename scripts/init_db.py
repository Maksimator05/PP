"""Initialize database schema."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.db import get_engine, init_database


if __name__ == "__main__":
    init_database(get_engine(), Path("sql/001_schema.sql"))
    print("Database schema initialized")
