"""Settings loaded from the current environment and .env file."""

import os
from typing import Any

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, SecretStr


class Settings(BaseModel):
    """Application settings; api_key is a SecretStr to hide it in repr."""

    api_key: SecretStr = SecretStr("")
    model: str = "~deepseek/deepseek-v4-flash-latest"
    base_url: str = "https://openrouter.ai/api/v1"
    db_path: str = "stayline.sqlite"
    memory_db_path: str = "stayline-memory.sqlite"
    checkpoint_db_path: str = "stayline-checkpoints.sqlite"
    insurer_id: str = "STAYLINE-VIE"
    max_model_calls: int = 12
    tool_timeout_s: float = 10.0
    model_timeout_s: float = 90.0
    phoenix_endpoint: str | None = None
    fault: str | None = None


def load_settings(**overrides: Any) -> Settings:
    """Load .env, then environment values, then explicit overrides."""
    load_dotenv(find_dotenv(usecwd=True))
    names = {
        "OPENROUTER_API_KEY": "api_key",
        "OPENROUTER_MODEL": "model",
        "OPENROUTER_BASE_URL": "base_url",
        "STAYLINE_DB": "db_path",
        "STAYLINE_MEMORY_DB": "memory_db_path",
        "STAYLINE_CHECKPOINT_DB": "checkpoint_db_path",
        "STAYLINE_FAULT": "fault",
        "PHOENIX_ENDPOINT": "phoenix_endpoint",
    }
    values = {
        field: value
        for name, field in names.items()
        if (value := os.getenv(name)) is not None
    }
    return Settings(**(values | overrides))
