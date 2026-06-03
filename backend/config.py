from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

OPENROUTER_MODEL = "deepseek/deepseek-v4-pro"


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    database_path: str = "./data/history.db"
    host: str = "127.0.0.1"
    port: int = 8000
    app_name: str = "ai-therapist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
