import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.memory import router as memory_router
from backend.api.videos import router as videos_router
from backend.container import AppContainer, build_container
from backend.core.config import get_settings
from backend.core.exceptions import (
    FrameNotFoundError,
    InvalidVideoError,
    MemoryUnavailableError,
    MnemosError,
    UnsupportedMediaTypeError,
    VideoNotFoundError,
    VideoTooLargeError,
)
from backend.reasoning.models import ReasoningError

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: list[tuple[type[MnemosError], int]] = [
    (UnsupportedMediaTypeError, 415),
    (VideoTooLargeError, 413),
    (InvalidVideoError, 400),
    (VideoNotFoundError, 404),
    (FrameNotFoundError, 404),
    (MemoryUnavailableError, 503),
]


async def _handle_mnemos_error(_: Request, exc: MnemosError) -> JSONResponse:
    status_code = next((code for cls, code in _STATUS_BY_ERROR if isinstance(exc, cls)), 500)
    return JSONResponse({"detail": str(exc)}, status_code=status_code)


async def _handle_reasoning_error(_: Request, exc: ReasoningError) -> JSONResponse:
    logger.warning("Reasoning failed: %s", exc)
    return JSONResponse({"detail": str(exc)}, status_code=502)


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
    app.add_exception_handler(ReasoningError, _handle_reasoning_error)
    origins = container.settings.frontend_origins if container else get_settings().frontend_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(videos_router)
    app.include_router(memory_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
