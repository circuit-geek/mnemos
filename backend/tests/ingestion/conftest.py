import io
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import backend.models  # noqa: F401  (register tables)
from backend.container import AppContainer
from backend.core.config import Settings
from backend.db.base import Base
from backend.db.session import create_session_factory
from backend.integrations.meta.sam_client import MockSamClient
from backend.integrations.storage.local import LocalObjectStorage
from backend.main import create_app

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sam_sample"
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class RecordingGraphWriter:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def write_video_graph(self, video_id, filename, created_at, result) -> None:
        self.calls.append((video_id, filename, result))

    async def close(self) -> None:
        return None


@pytest.fixture
def mp4_file() -> io.BytesIO:
    return io.BytesIO(MP4_BYTES)


@pytest.fixture
async def container(tmp_path: Path) -> AsyncIterator[AppContainer]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    container = AppContainer(
        settings=Settings(local_storage_path=tmp_path / "uploads"),
        engine=engine,
        session_factory=create_session_factory(engine),
        storage=LocalObjectStorage(tmp_path / "uploads"),
        sam=MockSamClient(FIXTURE_DIR),
        graph=RecordingGraphWriter(),
    )
    yield container
    await engine.dispose()


@pytest.fixture
async def client(container: AppContainer) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(container))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
