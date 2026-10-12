import pandas as pd

from retail_forecast.x5_loader import canonicalize_transactions


def test_duplicate_batch_does_not_create_duplicate_transactions(small_transactions: pd.DataFrame) -> None:
    doubled = pd.concat([small_transactions, small_transactions], ignore_index=True)
    canonical = canonicalize_transactions(doubled)
    deduped = canonical.drop_duplicates(subset=["transaction_id"])
    assert len(deduped) == len(small_transactions)
