from __future__ import annotations

import pandas as pd
import pytest

from retail_forecast.synthetic import generate_promo_texts, generate_transactions


@pytest.fixture()
def small_transactions() -> pd.DataFrame:
    return generate_transactions(seed=7, weeks=20, stores=2, categories=3)


@pytest.fixture()
def small_promo_texts(small_transactions: pd.DataFrame) -> pd.DataFrame:
    return generate_promo_texts(small_transactions, seed=7)
