"""X5 dataset discovery, profiling and canonical loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from retail_forecast.config import PROJECT_ROOT, load_yaml


def find_files(data_dir: Path, patterns: list[str]) -> list[Path]:
    """Find files matching configured patterns."""
    files: list[Path] = []
    for pattern in patterns:
        files.extend(data_dir.glob(pattern))
    return sorted(set(files))


def read_table(path: Path) -> pd.DataFrame:
    """Read CSV or parquet file."""
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {path}")


def load_mapping(path: Path = PROJECT_ROOT / "config" / "x5_data_mapping.yaml") -> dict[str, Any]:
    """Load data mapping configuration."""
    return load_yaml(path)


def canonicalize_transactions(frame: pd.DataFrame, mapping: dict[str, Any] | None = None) -> pd.DataFrame:
    """Map source columns into the canonical transaction schema."""
    mapping = mapping or load_mapping()
    fields = mapping["canonical_fields"]
    lower_to_original = {column.lower(): column for column in frame.columns}
    result = pd.DataFrame(index=frame.index)
    for canonical, aliases in fields.items():
        source = next((lower_to_original[alias.lower()] for alias in aliases if alias.lower() in lower_to_original), None)
        if source:
            result[canonical] = frame[source]

    if "transaction_id" not in result:
        result["transaction_id"] = [f"row-{idx}" for idx in range(len(frame))]
    if "store_id" not in result:
        result["store_id"] = "store_unknown"
    if "category_id" not in result:
        if "product_id" in result:
            result["category_id"] = result["product_id"].astype(str).map(lambda value: f"cat_hash_{abs(hash(value)) % 20:02d}")
        else:
            result["category_id"] = "cat_unknown"
    if "product_id" not in result:
        result["product_id"] = result["category_id"].astype(str) + "_sku_unknown"
    if "sales_amount" not in result:
        result["sales_amount"] = 0.0
    if "sales_quantity" not in result:
        result["sales_quantity"] = 1.0
    if "is_promo" not in result:
        result["is_promo"] = False
    if "promo_id" not in result:
        result["promo_id"] = ""
    if "transaction_date" not in result:
        raise ValueError("Required date column was not found in source data")

    result["transaction_date"] = pd.to_datetime(result["transaction_date"], errors="coerce")
    result["sales_amount"] = pd.to_numeric(result["sales_amount"], errors="coerce").fillna(0).clip(lower=0)
    result["sales_quantity"] = pd.to_numeric(result["sales_quantity"], errors="coerce").fillna(0).clip(lower=0)
    result["is_promo"] = result["is_promo"].fillna(False).astype(bool)
    for column in ["transaction_id", "store_id", "category_id", "product_id", "promo_id"]:
        result[column] = result[column].fillna("").astype(str)
    return result.dropna(subset=["transaction_date"])


def load_transactions(data_dir: Path, mapping: dict[str, Any] | None = None) -> pd.DataFrame:
    """Load all transaction-like files from a dataset directory."""
    mapping = mapping or load_mapping()
    files = find_files(data_dir, mapping["files"]["transactions"]["patterns"])
    if not files:
        raise FileNotFoundError(f"No transaction files found in {data_dir}")
    frames = [canonicalize_transactions(read_table(path), mapping) for path in files]
    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(subset=["transaction_id"])


def profile_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    """Build a lightweight data profile for documentation and tests."""
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "missing": {column: int(frame[column].isna().sum()) for column in frame.columns},
        "duplicates": int(frame.duplicated(subset=["transaction_id"]).sum()) if "transaction_id" in frame else int(frame.duplicated().sum()),
        "date_min": str(pd.to_datetime(frame["transaction_date"]).min().date()) if "transaction_date" in frame and len(frame) else "",
        "date_max": str(pd.to_datetime(frame["transaction_date"]).max().date()) if "transaction_date" in frame and len(frame) else "",
    }
