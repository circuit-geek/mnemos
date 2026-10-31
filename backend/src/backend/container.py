"""Shared long-lived dependencies, built once at startup (or injected by tests)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.db.session import create_engine, create_session_factory
from backend.integrations.meta.sam_client import SamClient, create_sam_client
from backend.integrations.neo4j.graph_writer import GraphWriter, Neo4jGraphWriter, NullGraphWriter
from backend.integrations.storage.base import ObjectStorage
from backend.integrations.storage.factory import create_storage
from backend.memory.repository import Neo4jMemoryRepository
from backend.reasoning.muse_client import MuseClient
from backend.reasoning.reasoning_service import ReasoningService
from backend.scene.scene_service import SceneAnalyzer


@dataclass
class AppContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    storage: ObjectStorage
    sam: SamClient
    graph: GraphWriter
    memory: Neo4jMemoryRepository | None = None
    reasoning: ReasoningService | None = None
    scene: SceneAnalyzer | None = None

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
    memory = graph.repository if isinstance(graph, Neo4jGraphWriter) else None
    reasoning = scene = None
    if memory is not None and settings.meta_api_key:
        muse = MuseClient(settings.meta_api_key, settings.muse_model)
        reasoning = ReasoningService(memory, muse)
        scene = SceneAnalyzer(
            muse,
            interval_ms=settings.scene_sample_interval_ms,
            min_confidence=settings.scene_min_confidence,
            concurrency=settings.scene_concurrency,
        )
    return AppContainer(
        settings=settings,
        engine=engine,
        session_factory=create_session_factory(engine),
        storage=create_storage(settings),
        sam=create_sam_client(settings),
        graph=graph,
        memory=memory,
        reasoning=reasoning,
        scene=scene,
    )
