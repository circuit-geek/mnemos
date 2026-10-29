"""Shared long-lived dependencies, built once at startup (or injected by tests)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.db.session import create_engine, create_session_factory
from backend.integrations.meta.sam_client import SamClient, create_sam_client
from backend.integrations.neo4j.graph_writer import GraphWriter, Neo4jGraphWriter, NullGraphWriter
from backend.integrations.storage.base import ObjectStorage
from backend.integrations.storage.factory import create_storage


@dataclass
class AppContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    storage: ObjectStorage
    sam: SamClient
    graph: GraphWriter

    async def close(self) -> None:
        await self.graph.close()
        await self.engine.dispose()


async def build_container(settings: Settings) -> AppContainer:
    engine = create_engine(settings.database_url)
    graph: GraphWriter = NullGraphWriter()
    if settings.neo4j_enabled:
        graph = await Neo4jGraphWriter.connect(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
            settings.neo4j_database,
        )
    return AppContainer(
        settings=settings,
        engine=engine,
        session_factory=create_session_factory(engine),
        storage=create_storage(settings),
        sam=create_sam_client(settings),
        graph=graph,
    )
