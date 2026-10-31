from backend.core.config import Settings
from backend.integrations.storage.base import ObjectStorage
from backend.integrations.storage.local import LocalObjectStorage


def create_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "local":
        return LocalObjectStorage(settings.local_storage_path)
    # TODO: Cloudflare R2 implementation of ObjectStorage (S3-compatible API).
    raise NotImplementedError(
        f"Storage backend {settings.storage_backend!r} is not implemented yet"
    )
