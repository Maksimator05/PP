from pathlib import Path

import pandas as pd

from retail_forecast.synthetic import write_synthetic_dataset
from retail_forecast.quality import validate_transactions
from retail_forecast.downloader import has_valid_dataset
from retail_forecast.x5_loader import canonicalize_transactions, load_transactions, profile_dataset


def test_loader_finds_files_and_profiles(tmp_path: Path) -> None:
    write_synthetic_dataset(tmp_path)
    transactions = load_transactions(tmp_path)
    profile = profile_dataset(transactions)
    assert profile["rows"] > 0
    assert {"transaction_id", "transaction_date", "sales_amount"}.issubset(transactions.columns)


def test_compressed_x5_purchase_lines_join_product_categories(tmp_path: Path) -> None:
    data_dir = tmp_path / "x5" / "data"
    data_dir.mkdir(parents=True)
    products = pd.DataFrame({"product_id": ["sku-a", "sku-b"], "level_2": ["молочные продукты", "хлеб"]})
    purchases = pd.DataFrame(
        {
            "client_id": ["client-1", "client-1"],
            "transaction_id": ["receipt-1", "receipt-1"],
            "transaction_datetime": ["2019-01-02 12:00:00", "2019-01-02 12:00:00"],
            "store_id": ["store-1", "store-1"],
            "product_id": ["sku-a", "sku-b"],
            "product_quantity": [2.0, 1.0],
            "purchase_sum": [300.0, 300.0],
            "trn_sum_from_iss": [200.0, 100.0],
            "trn_sum_from_red": [0.0, 0.0],
        }
    )
    products.to_csv(data_dir / "products.csv.gz", index=False, compression="gzip")
    purchases.to_csv(data_dir / "purchases.csv.gz", index=False, compression="gzip")

    assert has_valid_dataset(tmp_path / "x5")
    transactions = load_transactions(tmp_path / "x5")

    assert len(transactions) == 2
    assert transactions["transaction_id"].nunique() == 2
    assert set(transactions["category_id"]) == {"молочные продукты", "хлеб"}
    assert transactions["sales_amount"].sum() == 300.0
    assert validate_transactions(transactions)[1].empty


def test_canonicalization_keeps_bad_values_for_quality_rejection() -> None:
    source = pd.DataFrame(
        {
            "transaction_id": ["negative", "bad-date"],
            "transaction_date": ["2024-01-01", "not-a-date"],
            "store_id": ["s1", "s1"],
            "category_id": ["c1", "c1"],
            "sales_amount": [-3.0, 3.0],
            "sales_quantity": [1.0, 1.0],
        }
    )
    canonical = canonicalize_transactions(source)
    valid, rejected = validate_transactions(canonical)
    assert valid.empty
    assert set(rejected["issue_type"]) == {"negative_sales", "invalid_or_missing_date"}
