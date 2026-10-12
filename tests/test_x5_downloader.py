from pathlib import Path

from retail_forecast.downloader import has_valid_dataset
from retail_forecast.synthetic import write_synthetic_dataset


def test_existing_dataset_is_valid(tmp_path: Path) -> None:
    write_synthetic_dataset(tmp_path)
    assert has_valid_dataset(tmp_path)


def test_synthetic_fallback_files_created(tmp_path: Path) -> None:
    files = write_synthetic_dataset(tmp_path)
    assert files["transactions"].exists()
    assert files["promo_texts"].exists()
    assert has_valid_dataset(tmp_path)
