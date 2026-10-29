from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import BinaryIO, Protocol


class ObjectStorage(Protocol):
    """Where uploaded media lives. Application code only sees storage keys."""

    async def upload_file(self, key: str, data: BinaryIO, content_type: str) -> int:
        """Store `data` under `key`; return the number of bytes written."""

    async def get_download_reference(self, key: str) -> str:
        """A URL or path a trusted consumer can use to fetch the object."""

    async def delete_file(self, key: str) -> None:
        """Delete the object; missing keys are ignored."""

    def open_local_copy(self, key: str) -> AbstractAsyncContextManager[Path]:
        """Yield a local filesystem path for the object (downloaded to temp for remote stores)."""
