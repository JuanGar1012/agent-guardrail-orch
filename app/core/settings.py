from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    tool_timeout_seconds: float = 2.0
    db_path: str = "data/telemetry.db"
    enable_ollama: bool = False
    ollama_model: str = "llama3.2:3b"
    ollama_host: str = "http://127.0.0.1:11434"
    output_validation_retries: int = 1


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_settings(path: str | Path = "config/settings.yaml") -> AppSettings:
    data = load_yaml(path)
    return AppSettings(**data)
