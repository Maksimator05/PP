"""Data quality checks."""

from __future__ import annotations

import uuid

import pandas as pd


def validate_transactions(transactions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split valid and problematic transaction rows."""
    checks = pd.Series(True, index=transactions.index)
    issue_types: dict[int, str] = {}
    required = ["transaction_id", "transaction_date", "store_id", "category_id", "sales_amount", "sales_quantity"]
    for column in required:
        missing = transactions[column].isna() if column in transactions else pd.Series(True, index=transactions.index)
        for idx in transactions.index[missing]:
            issue_types[idx] = f"missing_{column}"
        checks &= ~missing
    invalid_date = pd.to_datetime(transactions["transaction_date"], errors="coerce").isna()
    for idx in transactions.index[invalid_date]:
        issue_types[idx] = "invalid_or_missing_date"
    checks &= ~invalid_date
    empty_category = transactions["category_id"].astype(str).str.strip().eq("")
    for idx in transactions.index[empty_category]:
        issue_types[idx] = "empty_category"
    checks &= ~empty_category
    negative = (transactions["sales_amount"] < 0) | (transactions["sales_quantity"] < 0)
    for idx in transactions.index[negative]:
        issue_types[idx] = "negative_sales"
    checks &= ~negative
    if len(transactions) > 20:
        threshold = transactions["sales_amount"].quantile(0.995) * 5
        anomalous = transactions["sales_amount"] > threshold
    else:
        anomalous = pd.Series(False, index=transactions.index)
    for idx in transactions.index[anomalous]:
        issue_types[idx] = "anomalous_sales_amount"
    checks &= ~anomalous
    duplicate = transactions.duplicated(subset=["transaction_id"], keep="first")
    for idx in transactions.index[duplicate]:
        issue_types[idx] = "duplicate_transaction"
    checks &= ~duplicate
    valid = transactions[checks].copy()
    rejected = transactions[~checks].copy()
    if not rejected.empty:
        rejected["issue_id"] = [str(uuid.uuid4()) for _ in range(len(rejected))]
        rejected["issue_type"] = [issue_types.get(idx, "unknown") for idx in rejected.index]
    return valid, rejected


def inject_bad_records(transactions: pd.DataFrame) -> pd.DataFrame:
    """Append deterministic bad records to demonstrate quality controls."""
    sample = transactions.head(1).copy()
    if sample.empty:
        return transactions
    bad_negative = sample.copy()
    bad_negative["transaction_id"] = "bad-negative-sales"
    bad_negative["sales_amount"] = -100
    bad_empty_category = sample.copy()
    bad_empty_category["transaction_id"] = "bad-empty-category"
    bad_empty_category["category_id"] = ""
    bad_missing_date = sample.copy()
    bad_missing_date["transaction_id"] = "bad-missing-date"
    bad_missing_date["transaction_date"] = pd.NaT
    duplicate = sample.copy()
    duplicate["transaction_id"] = sample.iloc[0]["transaction_id"]
    return pd.concat([transactions, bad_negative, bad_empty_category, bad_missing_date, duplicate], ignore_index=True)
