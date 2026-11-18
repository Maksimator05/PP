"""X5 dataset discovery, profiling and canonical loading."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from retail_forecast.config import PROJECT_ROOT, load_yaml


def find_files(data_dir: Path, patterns: list[str]) -> list[Path]:
    """Find files matching configured patterns."""
    files: list[Path] = []
    for pattern in patterns:
        files.extend(data_dir.rglob(pattern))
    return sorted(set(files))


def read_table(path: Path) -> pd.DataFrame:
    """Read CSV or parquet file."""
    if path.name.lower().endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, compression="infer", low_memory=False)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {path}")


def load_mapping(path: Path = PROJECT_ROOT / "config" / "x5_data_mapping.yaml") -> dict[str, Any]:
    """Load data mapping configuration."""
    return load_yaml(path)


def load_product_categories(data_dir: Path, mapping: dict[str, Any] | None = None) -> pd.DataFrame:
    """Read a product-to-category lookup from the optional product catalogue."""
    mapping = mapping or load_mapping()
    files = find_files(data_dir, mapping["files"].get("products", {}).get("patterns", []))
    if not files:
        return pd.DataFrame(columns=["product_id", "category_id"])
    products = read_table(files[0])
    lower = {column.lower(): column for column in products.columns}
    product_column = next((lower[key] for key in ("product_id", "sku", "item_id", "material") if key in lower), None)
    category_preference = mapping.get("product_category_fields", ["category_id", "product_category", "level_2", "level_3", "level_1", "category"])
    category_column = next((lower[key.lower()] for key in category_preference if key.lower() in lower), None)
    if product_column is None or category_column is None:
        return pd.DataFrame(columns=["product_id", "category_id"])
    result = products[[product_column, category_column]].rename(columns={product_column: "product_id", category_column: "category_id"})
    result = result.dropna(subset=["product_id", "category_id"]).drop_duplicates("product_id", keep="last")
    result["product_id"] = result["product_id"].astype(str)
    result["category_id"] = result["category_id"].astype(str)
    return result


def canonicalize_transactions(
    frame: pd.DataFrame,
    mapping: dict[str, Any] | None = None,
    product_categories: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Map source columns into the canonical transaction schema."""
    mapping = mapping or load_mapping()
    fields = mapping["canonical_fields"]
    lower_to_original = {column.lower(): column for column in frame.columns}
    result = pd.DataFrame(index=frame.index)
    for canonical, aliases in fields.items():
        source = next((lower_to_original[alias.lower()] for alias in aliases if alias.lower() in lower_to_original), None)
        if source:
            result[canonical] = frame[source]

    client_source = lower_to_original.get("client_id")
    if client_source:
        result["client_id"] = frame[client_source].fillna("").astype(str)

    if "product_id" not in result:
        product_source = next((lower_to_original[name] for name in ("sku", "item_id", "material") if name in lower_to_original), None)
        if product_source:
            result["product_id"] = frame[product_source]

    if "product_id" in result:
        result["product_id"] = result["product_id"].fillna("").astype(str)
    if "category_id" not in result and product_categories is not None and not product_categories.empty and "product_id" in result:
        result = result.merge(product_categories, on="product_id", how="left")

    if "sales_amount" not in result:
        iss_column = lower_to_original.get("trn_sum_from_iss")
        red_column = lower_to_original.get("trn_sum_from_red")
        purchase_column = lower_to_original.get("purchase_sum")
        if iss_column or red_column:
            iss = pd.to_numeric(frame[iss_column], errors="coerce") if iss_column else 0.0
            red = pd.to_numeric(frame[red_column], errors="coerce") if red_column else 0.0
            result["sales_amount"] = pd.Series(iss, index=frame.index).fillna(0) + pd.Series(red, index=frame.index).fillna(0)
        elif purchase_column:
            purchase = pd.to_numeric(frame[purchase_column], errors="coerce")
            # purchase_sum is receipt-level in X5 and repeats for each product row.
            # Use the product quantity share when line-level monetary fields are absent.
            if "product_id" in result and "transaction_id" in result and "sales_quantity" in result:
                client_column = lower_to_original.get("client_id")
                group_columns = ([frame[client_column].astype(str).rename("_client_id")] if client_column else []) + [result["transaction_id"].astype(str).rename("_transaction_id")]
                group_frame = pd.concat(group_columns, axis=1)
                quantity = pd.to_numeric(result["sales_quantity"], errors="coerce").fillna(0).abs()
                weights = quantity.groupby([group_frame[column] for column in group_frame.columns]).transform("sum")
                result["sales_amount"] = purchase * quantity.div(weights.where(weights != 0, 1))
            else:
                result["sales_amount"] = purchase

    if "transaction_id" not in result:
        result["transaction_id"] = [f"row-{idx}" for idx in range(len(frame))]
    if "store_id" not in result:
        result["store_id"] = "store_unknown"
    if "category_id" not in result:
        if "product_id" in result:
            result["category_id"] = result["product_id"].astype(str).map(
                lambda value: f"cat_hash_{int(sha256(value.encode('utf-8')).hexdigest()[:8], 16) % 20:02d}"
            )
        else:
            result["category_id"] = "cat_unknown"
    if "product_id" not in result:
        result["product_id"] = result["category_id"].astype(str) + "_sku_unknown"
    if "sales_quantity" not in result:
        result["sales_quantity"] = 1.0
    if "is_promo" not in result:
        result["is_promo"] = False
    if "promo_id" not in result:
        result["promo_id"] = ""
    if "transaction_date" not in result:
        raise ValueError("Required date column was not found in source data")

    result["transaction_date"] = pd.to_datetime(result["transaction_date"], errors="coerce")
    result["sales_amount"] = pd.to_numeric(result.get("sales_amount", pd.Series(index=result.index, dtype=float)), errors="coerce")
    result["sales_quantity"] = pd.to_numeric(result["sales_quantity"], errors="coerce")
    result["is_promo"] = result["is_promo"].map(_to_bool).fillna(False).astype(bool)
    for column in ["transaction_id", "store_id", "category_id", "product_id", "promo_id"]:
        result[column] = result[column].fillna("").astype(str)
    # Keep invalid dates and values for the quality gate so that rejected rows are auditable.
    return result


def _to_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "да", "promo", "promotion"}:
        return True
    if normalized in {"0", "false", "no", "n", "нет", "", "none", "nan"}:
        return False
    return None


def load_transactions(data_dir: Path, mapping: dict[str, Any] | None = None) -> pd.DataFrame:
    """Load all transaction-like files from a dataset directory."""
    mapping = mapping or load_mapping()
    files = find_files(data_dir, mapping["files"]["transactions"]["patterns"])
    if not files:
        raise FileNotFoundError(f"No transaction files found in {data_dir}")
    product_categories = load_product_categories(data_dir, mapping)
    frames = []
    for path in files:
        canonical = canonicalize_transactions(read_table(path), mapping, product_categories)
        canonical["_source_file"] = path.relative_to(data_dir).as_posix()
        frames.append(canonical)
    combined = pd.concat(frames, ignore_index=True)
    # X5 transaction_id is receipt-level, while its rows are product lines. Include
    # client and SKU when needed so a basket keeps every category line and remains unique.
    if combined["transaction_id"].duplicated().any():
        identity = combined["transaction_id"].astype(str)
        if "client_id" in combined:
            identity = combined["client_id"].astype(str) + "|" + identity
        if "product_id" in combined:
            identity = identity + "|" + combined["product_id"].astype(str)
        combined["transaction_id"] = identity
    combined = combined.drop(columns=["_source_file"])
    return combined.drop_duplicates(subset=["transaction_id"], keep="first")


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
