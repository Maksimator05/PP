"""Configuration loading utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_env_file(path: Path | str = PROJECT_ROOT / ".env") -> dict[str, str]:
    """Read a simple .env file without introducing a runtime dependency."""
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_yaml(path: Path | str) -> dict[str, Any]:
    """Load YAML from disk and return an empty mapping if the file is empty."""
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_config(path: Path | str = PROJECT_ROOT / "config" / "config.yaml") -> dict[str, Any]:
    """Load config and overlay selected environment variables."""
    config = load_yaml(path)
    file_env = read_env_file()

    def env(name: str, default: Any = None) -> Any:
        return os.getenv(name, file_env.get(name, default))

    config.setdefault("data", {})
    config.setdefault("forecast", {})
    config.setdefault("monitoring", {})
    config["data"]["source"] = env("DATA_SOURCE", config["data"].get("source", "synthetic"))
    config["data"]["x5_path"] = env("X5_DATA_PATH", config["data"].get("x5_path"))
    config["data"]["allow_download"] = str(env("X5_ALLOW_DOWNLOAD", config["data"].get("allow_download", True))).lower() == "true"
    config["forecast"]["horizon_weeks"] = int(env("FORECAST_HORIZON", config["forecast"].get("horizon_weeks", 1)))
    config["project"]["random_seed"] = int(env("RANDOM_SEED", config["project"].get("random_seed", 42)))
    config["database_url"] = env("DATABASE_URL", "sqlite:///data/processed/retail_forecast.sqlite")
    config["mlflow_tracking_uri"] = env("MLFLOW_TRACKING_URI", "file:./mlruns")
    return config


def project_path(value: str | Path) -> Path:
    """Resolve a project-relative path."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
