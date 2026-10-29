import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.videos import router as videos_router
from backend.container import AppContainer, build_container
from backend.core.config import get_settings
from backend.core.exceptions import (
    InvalidVideoError,
    MnemosError,
    UnsupportedMediaTypeError,
    VideoNotFoundError,
    VideoTooLargeError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: list[tuple[type[MnemosError], int]] = [
    (UnsupportedMediaTypeError, 415),
    (VideoTooLargeError, 413),
    (InvalidVideoError, 400),
    (VideoNotFoundError, 404),
]


async def _handle_mnemos_error(_: Request, exc: MnemosError) -> JSONResponse:
    status_code = next((code for cls, code in _STATUS_BY_ERROR if isinstance(exc, cls)), 500)
    return JSONResponse({"detail": str(exc)}, status_code=status_code)


def create_app(container: AppContainer | None = None) -> FastAPI:
    """`container` is injected by tests; otherwise it is built from settings at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        if owned:
            settings = get_settings()
            logging.basicConfig(level=settings.log_level)
            app.state.container = await build_container(settings)
        try:
            yield
        finally:
            if owned:
                await app.state.container.close()

    app = FastAPI(title="MNEMOS", lifespan=lifespan)
    if container is not None:
        app.state.container = container
    app.add_exception_handler(MnemosError, _handle_mnemos_error)
    app.include_router(videos_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
