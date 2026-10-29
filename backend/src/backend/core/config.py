"""Centralized application configuration (environment variables / .env)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://mnemos:mnemos@localhost:5432/mnemos"

    storage_backend: Literal["local", "r2"] = "local"
    local_storage_path: Path = BACKEND_ROOT / "data" / "uploads"
    max_upload_bytes: int = 500 * 1024 * 1024

    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str | None = None

    # "mock" replays saved experiment artifacts; "script" runs scripts/test_sam_video.py.
    sam_backend: Literal["mock", "script"] = "mock"
    sam_fixture_dir: Path = BACKEND_ROOT / "fixtures" / "sam_sample"
    sam_concept: str = "object"
    sam_script_path: Path = BACKEND_ROOT / "scripts" / "test_sam_video.py"
    meta_api_key: str = ""

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
