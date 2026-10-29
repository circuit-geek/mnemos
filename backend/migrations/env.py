import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import backend.models  # noqa: F401  (register tables on Base.metadata)
from backend.core.config import get_settings
from backend.db.base import Base

target_metadata = Base.metadata
database_url = get_settings().database_url


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_online())
