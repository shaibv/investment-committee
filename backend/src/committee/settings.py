"""Configuration and secrets, read from environment variables or backend/.env.

.env is git-ignored. .env.example (committed) documents what can be set.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # SecretStr keeps the key out of logs, tracebacks and repr() output.
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6-luna"


@lru_cache
def get_settings() -> Settings:
    return Settings()
