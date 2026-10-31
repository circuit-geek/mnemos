import asyncio
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import BinaryIO

from backend.core.exceptions import StorageError


class LocalObjectStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Storage key escapes the storage root")
        return path

    async def upload_file(self, key: str, data: BinaryIO, content_type: str) -> int:
        path = self._path(key)

        def write() -> int:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as out:
                shutil.copyfileobj(data, out, length=1024 * 1024)
            return path.stat().st_size

        return await asyncio.to_thread(write)

    async def get_download_reference(self, key: str) -> str:
        return str(self._path(key))

    async def delete_file(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    @asynccontextmanager
    async def open_local_copy(self, key: str) -> AsyncIterator[Path]:
        path = self._path(key)
        if not path.is_file():
            raise StorageError(f"Object not found: {key}")
        yield path
