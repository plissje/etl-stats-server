from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` next to the `backend/` package root (not the process cwd).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    stats_api_token: str = "dev-change-me"
    database_url: str = "sqlite:///./etl_stats.db"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:5180,"
        "http://localhost:5180"
    )


settings = Settings()
