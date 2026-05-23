from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` next to the `backend/` package root (not the process cwd).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT.parent / ".env"


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

    rcon_host: str = "127.0.0.1"
    rcon_port: int = 27960
    rcon_password: str = "dev-rcon-password"

    balancer_dampening_threshold: float = 3500.0
    balancer_dampening_factor: float = 0.5
    balancer_noise: float = 150.0
    balancer_max_diff: float = 350.0

settings = Settings()
