"""Runtime configuration for the assistant."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    MODEL_NAME: str = os.getenv("MODEL_NAME", "phi3:mini")
    MAX_CONTEXT_MESSAGES: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    GOOGLE_CALENDAR_ENABLED: bool = _as_bool(os.getenv("GOOGLE_CALENDAR_ENABLED", "false"))

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "assistant.db")
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")


settings = Settings()
