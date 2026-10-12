"""Automatic X5 RetailHero downloader with synthetic fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from retail_forecast.config import PROJECT_ROOT, load_config, project_path, read_env_file
from retail_forecast.logging_utils import setup_logger
from retail_forecast.synthetic import write_synthetic_dataset


EXPECTED_COLUMNS = {"transaction_date", "store_id", "category_id", "sales_amount", "sales_quantity"}


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
    candidates = list(path.glob("transactions*.csv")) + list(path.glob("*.parquet"))
    for candidate in candidates:
        try:
            if candidate.suffix == ".csv":
                sample = pd.read_csv(candidate, nrows=20)
            else:
                sample = pd.read_parquet(candidate)
            normalized = {column.lower() for column in sample.columns}
            if EXPECTED_COLUMNS.issubset(normalized) or {"client_id", "transaction_id"}.intersection(normalized):
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

    if has_valid_dataset(x5_path):
        logger.info("Existing dataset is valid: %s", x5_path)
        return DatasetStatus(x5_path, "x5_retailhero_local", False, _count_rows(x5_path), "Existing dataset reused")
    if data_source == "x5" and not force:
        message = f"DATA_SOURCE=x5 but no readable X5 files found in {x5_path}; synthetic fallback is blocked"
        logger.error(message)
        raise FileNotFoundError(message)
    if not force and has_valid_dataset(synthetic_path):
        logger.info("Existing synthetic fallback is valid: %s", synthetic_path)
        return DatasetStatus(synthetic_path, "existing_synthetic_fallback", True, _count_rows(synthetic_path), "Existing synthetic fallback reused")

    if config["data"].get("allow_download", True):
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
    else:
        logger.info("Download disabled by configuration")

    if data_source == "x5":
        message = "DATA_SOURCE=x5 and all public sources are unavailable; refusing silent synthetic fallback"
        logger.error(message)
        raise FileNotFoundError(message)

    logger.error("All public sources unavailable; creating explicit synthetic fallback")
    files = write_synthetic_dataset(synthetic_path, seed=int(config["project"]["random_seed"]))
    assumptions = PROJECT_ROOT / "docs" / "assumptions.md"
    assumptions.parent.mkdir(parents=True, exist_ok=True)
    if not assumptions.exists():
        assumptions.write_text("# Допущения\n\n", encoding="utf-8")
    marker = "- Использован синтетический fallback, потому что публичные источники X5 недоступны в текущей среде.\n"
    text = assumptions.read_text(encoding="utf-8")
    if marker not in text:
        assumptions.write_text(text.rstrip() + "\n" + marker, encoding="utf-8")
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
    candidates = list(path.glob("transactions*.csv"))
    if not candidates:
        return 0
    return sum(len(pd.read_csv(candidate, usecols=[0])) for candidate in candidates)
