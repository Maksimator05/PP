from pathlib import Path

from retail_forecast.synthetic import write_synthetic_dataset
from retail_forecast.x5_loader import load_transactions, profile_dataset


def test_loader_finds_files_and_profiles(tmp_path: Path) -> None:
    write_synthetic_dataset(tmp_path)
    transactions = load_transactions(tmp_path)
    profile = profile_dataset(transactions)
    assert profile["rows"] > 0
    assert {"transaction_id", "transaction_date", "sales_amount"}.issubset(transactions.columns)
