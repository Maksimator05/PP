"""Deterministic synthetic fallback data for offline demonstrations."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROMO_TEMPLATES = [
    "Скидка {discount}% на категорию {category}. Выгода недели.",
    "Промо bundle для категории {category}: два товара по специальной цене.",
    "Новинка в категории {category}. Поддержка продаж в сезонный период.",
    "Распродажа остатков категории {category} со скидкой {discount}%.",
]


def generate_transactions(seed: int = 42, weeks: int = 120, stores: int = 4, categories: int = 8) -> pd.DataFrame:
    """Generate transaction-level data with trend, seasonality, promo effects and noise."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-02")
    rows: list[dict[str, object]] = []
    tx_id = 1
    for week_idx in range(weeks):
        week_start = start + pd.Timedelta(weeks=week_idx)
        for store in range(1, stores + 1):
            for category in range(1, categories + 1):
                base = 600 + category * 55 + store * 35 + week_idx * 2.5
                season = 90 * np.sin(2 * np.pi * week_idx / 52 + category / 3)
                is_promo = (week_idx + category + store) % 6 == 0
                promo_boost = 1.25 if is_promo else 1.0
                amount = max(20, (base + season) * promo_boost + rng.normal(0, 45))
                quantity = max(1, amount / rng.uniform(70, 130))
                transactions = max(2, int(rng.poisson(4)))
                for item in range(transactions):
                    part = rng.uniform(0.12, 0.35)
                    rows.append(
                        {
                            "transaction_id": f"synthetic-{tx_id:08d}",
                            "transaction_date": (week_start + pd.Timedelta(days=int(rng.integers(0, 7)))).date(),
                            "store_id": f"store_{store:02d}",
                            "category_id": f"cat_{category:02d}",
                            "product_id": f"sku_{category:02d}_{item % 6:02d}",
                            "sales_amount": round(float(amount * part), 2),
                            "sales_quantity": round(float(quantity * part), 3),
                            "is_promo": bool(is_promo),
                            "promo_id": f"promo_{week_idx:03d}_{category:02d}" if is_promo else "",
                        }
                    )
                    tx_id += 1
    return pd.DataFrame(rows)


def generate_promo_texts(transactions: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate weakly structured promo descriptions tied to promo periods."""
    rng = np.random.default_rng(seed)
    promo_rows = transactions.loc[transactions["is_promo"], ["promo_id", "store_id", "category_id", "transaction_date"]].copy()
    if promo_rows.empty:
        return pd.DataFrame(columns=["promo_id", "store_id", "category_id", "week_start", "promo_text"])
    promo_rows["transaction_date"] = pd.to_datetime(promo_rows["transaction_date"])
    promo_rows["week_start"] = promo_rows["transaction_date"] - pd.to_timedelta(promo_rows["transaction_date"].dt.weekday, unit="D")
    promo_rows = promo_rows.drop_duplicates(["promo_id", "store_id", "category_id", "week_start"])
    texts = []
    for row in promo_rows.itertuples(index=False):
        discount = int(rng.choice([10, 15, 20, 25, 30]))
        template = PROMO_TEMPLATES[int(rng.integers(0, len(PROMO_TEMPLATES)))]
        texts.append(template.format(discount=discount, category=row.category_id))
    promo_rows["promo_text"] = texts
    return promo_rows[["promo_id", "store_id", "category_id", "week_start", "promo_text"]]


def write_synthetic_dataset(output_dir: Path, seed: int = 42) -> dict[str, Path]:
    """Write fallback CSV files and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    transactions = generate_transactions(seed=seed)
    promo_texts = generate_promo_texts(transactions, seed=seed)
    transactions_path = output_dir / "transactions.csv"
    promo_path = output_dir / "promo_texts.csv"
    transactions.to_csv(transactions_path, index=False)
    promo_texts.to_csv(promo_path, index=False)
    manifest = output_dir / "MANIFEST.txt"
    manifest.write_text(
        "synthetic_fallback=true\n"
        f"transactions_rows={len(transactions)}\n"
        f"promo_rows={len(promo_texts)}\n",
        encoding="utf-8",
    )
    return {"transactions": transactions_path, "promo_texts": promo_path, "manifest": manifest}
