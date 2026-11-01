class MnemosError(Exception):
    """Base class for expected application errors."""


class InvalidVideoError(MnemosError):
    """Uploaded video failed validation."""


class UnsupportedMediaTypeError(InvalidVideoError):
    pass


class VideoTooLargeError(InvalidVideoError):
    pass


class VideoNotFoundError(MnemosError):
    pass


class SamProcessingError(MnemosError):
    """SAM invocation or output parsing failed."""


class StorageError(MnemosError):
    pass


class StorageObjectNotFoundError(StorageError):
    """The stored file for a recording is missing (e.g. removed from disk)."""


class MemoryUnavailableError(MnemosError):
    """Temporal memory (Neo4j) or reasoning (Muse) is not configured."""


class VideoBusyError(MnemosError):
    """The video is still being processed and cannot be changed or deleted yet."""


class FrameNotFoundError(MnemosError):
    """No frame could be extracted at the requested timestamp."""
