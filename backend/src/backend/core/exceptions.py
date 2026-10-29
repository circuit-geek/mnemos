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
