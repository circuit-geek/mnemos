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
    # Used only when discovery finds nothing.
    sam_concept: str = "object"
    # What to track is per video: the upload's `concepts`, else discovered by Muse Spark.
    sam_discovery_frames: int = 6
    sam_max_concepts: int = 5
    sam_script_path: Path = BACKEND_ROOT / "scripts" / "test_sam_video.py"
    meta_api_key: str = ""
    muse_model: str = "muse-spark-1.3"

    scene_sample_interval_ms: int = 2000
    scene_min_confidence: float = 0.6
    scene_concurrency: int = 4

    # Comma-separated origins allowed to call the API from a browser.
    frontend_origins: str = "http://localhost:5173"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
