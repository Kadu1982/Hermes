from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HERMES_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hermes:hermes@localhost:5432/hermes"
    jwt_secret: str = "dev-insecure-change-me"
    access_token_expire_minutes: int = 10080  # 7 dias (app móvel)
    files_dir: Path = Path("./data/files")
    max_upload_mb: int = 20
    pairing_pepper: str = "dev-pepper-change-me"
    cors_origins: str = "http://localhost:3000"
    brain_service_key: str = ""  # HERMES_BRAIN_SERVICE_KEY — gateway ~/.hermes → API dispositivos
    brain_api_public_url: str = "http://127.0.0.1:18080"  # URL que o CLI na VPS usa
    google_workspace_python: Path = Path.home() / ".hermes/google-venv/bin/python"
    google_workspace_setup_script: Path = Path.home() / ".hermes/skills/productivity/google-workspace/scripts/setup.py"
    google_workspace_api_script: Path = Path.home() / ".hermes/skills/productivity/google-workspace/scripts/google_api.py"


@lru_cache
def get_settings() -> Settings:
    return Settings()
