"""Automatic X5 RetailHero downloader with synthetic fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from retail_forecast.config import load_config, project_path, read_env_file
from retail_forecast.logging_utils import setup_logger
from retail_forecast.synthetic import write_synthetic_dataset


DATE_ALIASES = {"transaction_date", "date", "purchased_at", "transaction_datetime", "day"}
PRODUCT_ALIASES = {"product_id", "sku", "item_id", "material"}
CATEGORY_ALIASES = {"category_id", "product_category", "level_2", "level_3", "level_1", "category"}
AMOUNT_ALIASES = {"sales_amount", "line_amount", "amount", "revenue", "line_total", "net_sales", "trn_sum_from_iss", "trn_sum_from_red", "purchase_sum"}


@dataclass(frozen=True)
class DatasetStatus:
    """Result of dataset initialization."""

    path: Path
    source: str
    is_synthetic: bool
    rows: int
    message: str


def has_valid_dataset(path: Path) -> bool:
    """Return True when a usable transaction file already exists."""
    if not path.exists():
        return False
    candidates = (
        list(path.rglob("transactions*.csv"))
        + list(path.rglob("transactions*.csv.gz"))
        + list(path.rglob("transactions*.parquet"))
        + list(path.rglob("purchases*.csv"))
        + list(path.rglob("purchases*.csv.gz"))
        + list(path.rglob("purchases*.parquet"))
    )
    for candidate in candidates:
        try:
            if candidate.name.lower().endswith((".csv", ".csv.gz")):
                sample = pd.read_csv(candidate, nrows=20, compression="infer", low_memory=False)
            elif candidate.suffix.lower() == ".parquet":
                sample = pd.read_parquet(candidate)
            else:
                continue
            normalized = {column.lower() for column in sample.columns}
            has_date = bool(normalized & DATE_ALIASES)
            has_amount = bool(normalized & AMOUNT_ALIASES)
            has_product_dimension = bool(normalized & (PRODUCT_ALIASES | CATEGORY_ALIASES))
            if has_date and has_amount and has_product_dimension:
                return True
        except Exception:
            continue
    return False


def _retry(operation: Callable[[], None], attempts: int = 3, base_delay: float = 0.5) -> None:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            operation()
            return
        except Exception as exc:  # pragma: no cover - precise network failures vary
            last_error = exc
            time.sleep(base_delay * (2**attempt))
    if last_error:
        raise last_error


def try_huggingface_download(dataset_id: str, output_dir: Path) -> bool:
    """Try downloading from HuggingFace if the optional dependency is installed."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return False

    def operation() -> None:
        snapshot_download(repo_id=dataset_id, repo_type="dataset", local_dir=output_dir, local_dir_use_symlinks=False)

    _retry(operation)
    return has_valid_dataset(output_dir)


def try_kaggle_download(output_dir: Path, env: dict[str, str]) -> bool:
    """Try Kaggle only when credentials are configured."""
    if not env.get("KAGGLE_USERNAME") or not env.get("KAGGLE_KEY"):
        return False
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        return False
    api = KaggleApi()
    api.authenticate()
    output_dir.mkdir(parents=True, exist_ok=True)
    api.dataset_download_files("shonenkov/x5retailheroupliftrawdata", path=output_dir, unzip=True)
    return has_valid_dataset(output_dir)


def ensure_dataset(force: bool = False) -> DatasetStatus:
    """Ensure data is available locally, downloading once or creating a transparent fallback."""
    config = load_config()
    env = read_env_file()
    logger = setup_logger("retail_forecast.downloader", "download.log")
    x5_path = project_path(config["data"]["x5_path"])
    synthetic_path = project_path(config["data"].get("synthetic_path", "data/raw/x5_retailhero_synthetic"))
    data_source = str(config["data"].get("source", "synthetic")).lower()

    if data_source == "x5" and has_valid_dataset(x5_path):
        logger.info("Existing X5 dataset is valid: %s", x5_path)
        return DatasetStatus(x5_path, "x5_retailhero_local", False, _count_rows(x5_path), "Existing dataset reused")
    if data_source != "x5" and not force and has_valid_dataset(synthetic_path):
        logger.info("Existing synthetic fallback is valid: %s", synthetic_path)
        return DatasetStatus(synthetic_path, "existing_synthetic_fallback", True, _count_rows(synthetic_path), "Existing synthetic fallback reused")

    # A synthetic demo is deliberately offline. Network downloads happen only for
    # the explicit X5 mode or when the download command is forced.
    should_download = data_source == "x5" or force
    if should_download and config["data"].get("allow_download", True):
        dataset_id = env.get("X5_HF_DATASET_ID", "pytorch-lifestream/retailhero-uplift")
        for source_name, attempt in [
            ("huggingface", lambda: try_huggingface_download(dataset_id, x5_path)),
            ("kaggle", lambda: try_kaggle_download(x5_path, env)),
        ]:
            try:
                logger.info("Trying %s source", source_name)
                if attempt():
                    rows = _count_rows(x5_path)
                    logger.info("Dataset downloaded from %s, rows=%s", source_name, rows)
                    return DatasetStatus(x5_path, source_name, False, rows, f"Downloaded from {source_name}")
            except Exception as exc:
                logger.warning("%s source failed: %s", source_name, exc)
    elif should_download:
        logger.info("Download disabled by configuration")

    if data_source == "x5":
        message = "DATA_SOURCE=x5 and all public sources are unavailable; refusing silent synthetic fallback"
        logger.error(message)
        raise FileNotFoundError(message)

    logger.error("All public sources unavailable; creating explicit synthetic fallback")
    files = write_synthetic_dataset(synthetic_path, seed=int(config["project"]["random_seed"]))
    rows = len(pd.read_csv(files["transactions"]))
    return DatasetStatus(synthetic_path, "synthetic_fallback", True, rows, "Synthetic fallback generated")


def verify_x5_dataset() -> DatasetStatus:
    """Verify that local X5 files are present and readable without fallback."""
    config = load_config()
    x5_path = project_path(config["data"]["x5_path"])
    if not has_valid_dataset(x5_path):
        raise FileNotFoundError(f"X5 RetailHero files were not found or are unreadable in {x5_path}")
    return DatasetStatus(x5_path, "x5_retailhero_local", False, _count_rows(x5_path), "X5 dataset verified")


def _count_rows(path: Path) -> int:
    candidates = (
        list(path.rglob("transactions*.csv"))
        + list(path.rglob("transactions*.csv.gz"))
        + list(path.rglob("transactions*.parquet"))
        + list(path.rglob("purchases*.csv"))
        + list(path.rglob("purchases*.csv.gz"))
        + list(path.rglob("purchases*.parquet"))
    )
    total = 0
    for candidate in candidates:
        if candidate.name.lower().endswith((".csv", ".csv.gz")):
            total += sum(len(chunk) for chunk in pd.read_csv(candidate, usecols=[0], compression="infer", chunksize=500_000))
        elif candidate.suffix.lower() == ".parquet":
            total += len(pd.read_parquet(candidate))
    return total
