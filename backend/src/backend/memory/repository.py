"""Neo4j persistence for request-scoped tracking memory."""

from neo4j import GraphDatabase

from .models import Event, MemoryBatch, Observation, TrackedObject, Video


SCHEMA = (
    "CREATE CONSTRAINT video_id_unique IF NOT EXISTS FOR (n:Video) REQUIRE n.video_id IS UNIQUE",
    "CREATE CONSTRAINT object_id_unique IF NOT EXISTS FOR (n:Object) REQUIRE n.object_id IS UNIQUE",
    "CREATE CONSTRAINT observation_id_unique IF NOT EXISTS FOR (n:Observation) REQUIRE n.observation_id IS UNIQUE",
    "CREATE CONSTRAINT location_id_unique IF NOT EXISTS FOR (n:Location) REQUIRE n.location_id IS UNIQUE",
    "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (n:Event) REQUIRE n.event_id IS UNIQUE",
    "CREATE INDEX object_video_tracking IF NOT EXISTS FOR (n:Object) ON (n.video_id, n.tracking_id)",
    "CREATE INDEX observation_frame IF NOT EXISTS FOR (n:Observation) ON (n.video_id, n.frame_index)",
    "CREATE INDEX observation_time IF NOT EXISTS FOR (n:Observation) ON (n.object_id, n.timestamp_ms)",
    "CREATE INDEX event_video_time IF NOT EXISTS FOR (n:Event) ON (n.video_id, n.start_time_ms)",
)

CREATE_VIDEO = """
MERGE (v:Video {video_id: $video_id})
ON CREATE SET v.created_at = $created_at
SET v.filename = $filename, v.duration_ms = $duration_ms
"""

UPSERT_OBJECT = """
MATCH (v:Video {video_id: $video_id})
MERGE (o:Object {object_id: $object_id})
SET o.video_id = $video_id, o.tracking_id = $tracking_id,
    o.label = $label, o.first_seen_ms = $first_seen_ms,
    o.last_seen_ms = $last_seen_ms
MERGE (v)-[:HAS_OBJECT]->(o)
"""

SAVE_OBSERVATIONS = """
UNWIND $rows AS row
MATCH (v:Video {video_id: row.video_id})
MATCH (o:Object {object_id: row.object_id})
MERGE (obs:Observation {observation_id: row.observation_id})
SET obs.video_id = row.video_id, obs.object_id = row.object_id,
    obs.timestamp_ms = row.timestamp_ms, obs.frame_index = row.frame_index,
    obs.bounding_box = row.bounding_box, obs.confidence = row.confidence,
    obs.evidence_uri = row.evidence_uri
MERGE (v)-[:CONTAINS]->(obs)
MERGE (o)-[:HAS_OBSERVATION]->(obs)
"""

CREATE_EVENT = """
MATCH (v:Video {video_id: $video_id})
MATCH (o:Object {object_id: $object_id})
MERGE (e:Event {event_id: $event_id})
SET e.video_id = $video_id, e.object_id = $object_id,
    e.event_type = $event_type, e.start_time_ms = $start_time_ms,
    e.end_time_ms = $end_time_ms, e.description = $description,
    e.confidence = $confidence
MERGE (v)-[:HAS_EVENT]->(e)
MERGE (o)-[:PARTICIPATED_IN]->(e)
WITH e
UNWIND $source_observation_ids AS source_id
MATCH (source:Observation {observation_id: source_id})
MERGE (e)-[:DERIVED_FROM]->(source)
"""


def _properties(model):
    return model.model_dump(exclude_none=False)


def _created(result):
    return result.consume().counters.nodes_created


def _node(record, key):
    return dict(record[key])


class Neo4jMemoryRepository:
    def __init__(self, driver, database: str | None = None):
        self.driver = driver
        self.database = database

    @classmethod
    def connect(cls, uri: str, username: str, password: str, database: str | None = None):
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        return cls(driver, database)

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def initialize_schema(self):
        with self.driver.session(database=self.database) as session:
            for statement in SCHEMA:
                session.run(statement).consume()

    @staticmethod
    def _create_video(tx, video: Video) -> int:
        return _created(tx.run(CREATE_VIDEO, **_properties(video)))

    @staticmethod
    def _upsert_object(tx, tracked: TrackedObject) -> int:
        return _created(tx.run(UPSERT_OBJECT, **_properties(tracked)))

    @staticmethod
    def _save_observations(tx, observations: list[Observation]) -> int:
        if not observations:
            return 0
        return _created(tx.run(SAVE_OBSERVATIONS, rows=[_properties(o) for o in observations]))

    @staticmethod
    def _create_event(tx, event: Event) -> int:
        return _created(tx.run(CREATE_EVENT, **_properties(event)))

    def create_video(self, video: Video) -> int:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(self._create_video, video)

    def upsert_object(self, tracked: TrackedObject) -> int:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(self._upsert_object, tracked)

    def save_observations(self, observations: list[Observation]) -> int:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(self._save_observations, observations)

    def create_event(self, event: Event) -> int:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(self._create_event, event)

    def ingest(self, batch: MemoryBatch, events: list[Event]) -> int:
        """Write one complete video batch atomically; return newly created object count."""
        def write(tx):
            self._create_video(tx, batch.video)
            created = sum(self._upsert_object(tx, tracked) for tracked in batch.objects)
            self._save_observations(tx, batch.observations)
            for event in events:
                self._create_event(tx, event)
            return created

        with self.driver.session(database=self.database) as session:
            return session.execute_write(write)

    def get_video_objects(self, video_id: str) -> list[dict]:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_OBJECT]->(o:Object)
                   RETURN o ORDER BY o.first_seen_ms, o.object_id"""
        with self.driver.session(database=self.database) as session:
            return [_node(record, "o") for record in session.execute_read(
                lambda tx: list(tx.run(query, video_id=video_id)))]

    def get_object_history(self, video_id: str, object_id: str) -> list[dict]:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_OBJECT]->(o:Object {object_id: $object_id})
                   MATCH (o)-[:HAS_OBSERVATION]->(obs:Observation)
                   RETURN obs ORDER BY obs.timestamp_ms, obs.frame_index"""
        with self.driver.session(database=self.database) as session:
            return [_node(record, "obs") for record in session.execute_read(
                lambda tx: list(tx.run(query, video_id=video_id, object_id=object_id)))]

    def get_video_events(self, video_id: str) -> list[dict]:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_EVENT]->(e:Event)
                   RETURN e ORDER BY e.start_time_ms, e.event_id"""
        with self.driver.session(database=self.database) as session:
            return [_node(record, "e") for record in session.execute_read(
                lambda tx: list(tx.run(query, video_id=video_id)))]

    def get_last_observed_position(self, video_id: str, object_id: str) -> dict | None:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_OBJECT]->(o:Object {object_id: $object_id})
                   MATCH (o)-[:HAS_OBSERVATION]->(obs:Observation)
                   RETURN obs ORDER BY obs.timestamp_ms DESC, obs.frame_index DESC LIMIT 1"""
        with self.driver.session(database=self.database) as session:
            records = session.execute_read(
                lambda tx: list(tx.run(query, video_id=video_id, object_id=object_id)))
            return _node(records[0], "obs") if records else None

    def get_observation_at_or_before(self, video_id: str, object_id: str, timestamp_ms: int) -> dict | None:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_OBJECT]->(o:Object {object_id: $object_id})
                   MATCH (o)-[:HAS_OBSERVATION]->(obs:Observation)
                   WHERE obs.timestamp_ms <= $timestamp_ms
                   RETURN obs ORDER BY obs.timestamp_ms DESC, obs.frame_index DESC LIMIT 1"""
        with self.driver.session(database=self.database) as session:
            records = session.execute_read(lambda tx: list(tx.run(
                query, video_id=video_id, object_id=object_id, timestamp_ms=timestamp_ms)))
            return _node(records[0], "obs") if records else None

    def get_moved_objects(self, video_id: str) -> list[dict]:
        query = """MATCH (:Video {video_id: $video_id})-[:HAS_EVENT]->(:Event {event_type: 'MOVED'})
                   <-[:PARTICIPATED_IN]-(o:Object)
                   RETURN DISTINCT o ORDER BY o.object_id"""
        with self.driver.session(database=self.database) as session:
            return [_node(record, "o") for record in session.execute_read(
                lambda tx: list(tx.run(query, video_id=video_id)))]
