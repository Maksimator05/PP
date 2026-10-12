"""Offline feature extraction from weakly structured promo text."""

from __future__ import annotations

import re

import pandas as pd


POSITIVE_WORDS = {"выгода", "скидка", "подарок", "новинка", "лучший"}
NEGATIVE_WORDS = {"остатки", "распродажа", "срок", "возврат"}


def extract_discount(text: str) -> float:
    """Extract the maximum discount percentage from text."""
    values = [float(match) for match in re.findall(r"(\d{1,2})\s*%", text or "")]
    return max(values) if values else 0.0


def build_text_features(promo_texts: pd.DataFrame) -> pd.DataFrame:
    """Create numeric text features without external dictionaries."""
    if promo_texts.empty:
        return pd.DataFrame(columns=["store_id", "category_id", "week_start"])
    result = promo_texts.copy()
    text = result["promo_text"].fillna("").str.lower()
    result["promo_text_len"] = text.str.len()
    result["promo_word_count"] = text.str.split().map(len)
    result["promo_discount_pct"] = text.map(extract_discount)
    result["promo_has_bundle"] = text.str.contains("bundle|набор|два товара", regex=True).astype(int)
    result["promo_has_new"] = text.str.contains("новинка|новый", regex=True).astype(int)
    result["promo_has_sale"] = text.str.contains("скидка|распродажа|выгода", regex=True).astype(int)
    result["promo_positive_words"] = text.map(lambda value: sum(word in value for word in POSITIVE_WORDS))
    result["promo_negative_words"] = text.map(lambda value: sum(word in value for word in NEGATIVE_WORDS))
    result["week_start"] = pd.to_datetime(result["week_start"])
    columns = [
        "store_id",
        "category_id",
        "week_start",
        "promo_text_len",
        "promo_word_count",
        "promo_discount_pct",
        "promo_has_bundle",
        "promo_has_new",
        "promo_has_sale",
        "promo_positive_words",
        "promo_negative_words",
    ]
    return result[columns].groupby(["store_id", "category_id", "week_start"], as_index=False).max()
