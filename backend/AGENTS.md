# MNEMOS Backend — Agent Development Instructions

## 1. Backend Overview

The MNEMOS backend is responsible for transforming visual observations into persistent, queryable temporal memory.

It provides APIs for:

- Video ingestion.
- Video processing and tracking.
- Object observation management.
- Scene understanding.
- Temporal knowledge graph construction.
- Event generation.
- Historical memory retrieval.
- Natural-language question answering.

The backend must remain modular, testable, and runnable on its own (the frontend is a separate client of its HTTP API).

Follow the repository-wide instructions in the root `AGENTS.md`.

---

## 2. Technology Stack

Use:

- Python 3.12+
- FastAPI
- Pydantic v2
- pydantic-settings
- uv
- Neo4j Python driver
- Meta Model API
- OpenCV / FFmpeg
- pytest
- pytest-asyncio

Prefer Python's standard library where practical.

Do not introduce additional frameworks unless required by a concrete feature.

---

## 5. Core Backend Engines

The backend consists of four logical engines.

These are logical application components, not independently deployed microservices.

### 5.1 Perception Engine

Responsible for extracting structured observations from visual input.

Primary modules:

- `sam_client.py`
- `sam_parser.py`
- `perception_service.py`

The SAM client handles communication with Meta's API.

The parser converts model-specific responses into normalized internal structures.

The perception service coordinates segmentation and tracking operations.

### Important Rules

- Preserve original model responses during development for debugging.
- Parse outputs using documented formats.
- Validate frame indices and bounding boxes.
- Preserve tracking IDs from model responses.
- Never assume tracking IDs are globally unique.
- Associate observations with their source video.
- Avoid unnecessary repeated API calls.
- Use cached responses for deterministic tests.

Bounding boxes should use a consistent documented coordinate convention.

Store timestamps in seconds relative to the video start.

When source frames are sampled, preserve the actual frame timestamps.

Do not assume all videos use a fixed frame rate.

### 5.2 Scene Intelligence Engine

Responsible for identifying semantic relationships between observed objects.

Primary modules:

- `scene_service.py`
- `muse_client.py`

The scene intelligence engine may combine:

- Bounding-box geometry.
- Segmentation masks.
- Semantic object labels.
- Muse Spark multimodal reasoning.

Relationships must use known object identifiers.

Supported MVP relationship types:

- `ON`
- `NEXT_TO`
- `NEAR`
- `INSIDE`
- `CONTAINS`

Only emit relationships supported by available evidence.

Do not infer physical relationships solely from overlapping bounding boxes.

Use validated, structured model outputs.

### 5.3 Memory Engine

Responsible for preserving temporal observations and relationships.

Primary modules:

- `identity_service.py`
- `memory_service.py`
- `event_service.py`
- Graph repositories.

The memory engine must:

1. Register persistent objects.
2. Associate observations with object identities.
3. Track object visibility over time.
4. Maintain historical relationships.
5. Detect meaningful state transitions.
6. Generate timestamped memory events.
7. Preserve references to supporting evidence.

Do not overwrite historical observations.

Do not delete previous relationships merely because they are absent from a later frame.

Maintain explicit uncertainty for ambiguous changes.

### 5.4 Reasoning Engine

Responsible for answering natural-language questions about stored memory.

Primary module:

- `reasoning_service.py`

The reasoning pipeline is:

```text
Question
   |
   v
Query Interpretation
   |
   v
Validated Query Intent
   |
   v
Graph Retrieval
   |
   v
Evidence Retrieval
   |
   v
Muse Spark Answer Generation
   |
   v
Validated Answer
```

Support these initial query intents:

- `LAST_SEEN`
- `CHANGES`
- `OBJECT_HISTORY`
- `SCENE_AT_TIME`
- `RELATIONSHIPS`

Use deterministic Cypher query templates for the MVP.

Do not allow unrestricted model-generated Cypher queries.

Muse Spark must not directly modify Neo4j.

Model-generated answers must reference retrieved evidence.

If information is insufficient, return an explicit uncertainty or insufficient-evidence response.

---

## 6. Temporal Knowledge Graph

Neo4j is the primary graph database.

### Node Types

#### Video

Represents a recording.

Suggested properties:

- `id`
- `title`
- `duration_seconds`
- `status`
- `created_at`
- `media_reference`

#### Object

Represents a persistent object identity.

Suggested properties:

- `id`
- `video_id`
- `label`
- `first_seen`
- `last_seen`

#### Observation

Represents a timestamped observation.

Suggested properties:

- `id`
- `object_id`
- `video_id`
- `frame_index`
- `timestamp_seconds`
- `bounding_box`
- `visibility`
- `evidence_reference`

#### Event

Represents a significant observation or relationship change.

Suggested properties:

- `id`
- `video_id`
- `event_type`
- `timestamp_seconds`
- `description`
- `confidence_state`

#### Location

Represents a semantic location or scene region.

Suggested properties:

- `id`
- `video_id`
- `name`
- `location_type`

### Relationships

Possible graph relationships:

- `HAS_OBJECT`
- `HAS_OBSERVATION`
- `HAS_EVENT`
- `OBSERVED_AS`
- `AFFECTS`
- `ON`
- `NEAR`
- `NEXT_TO`
- `INSIDE`
- `CONTAINS`

Spatial relationships should contain:

- `relationship_id`
- `valid_from`
- `valid_to`
- `evidence_id`
- `confidence_state`

Use half-open validity intervals where practical:

`valid_from <= timestamp < valid_to`

A null `valid_to` indicates an open interval.

### Temporal Integrity

- Preserve historical relationships.
- Do not create overlapping contradictory validity intervals without explicitly modeling uncertainty.
- Keep graph updates idempotent.
- Use stable identifiers.
- Create constraints for unique identifiers.
- Use parameterized Cypher queries.
- Use database transactions for logically related graph updates.
- Ensure repeated processing does not create duplicate observations or events.

A visibility gap must not automatically terminate a physical relationship.

When the evidence is insufficient, preserve the last known relationship while marking the current state as unverified or unknown.

---

## 7. Object Identity Management

SAM may assign tracking IDs that are valid only within a particular request or session.

MNEMOS must maintain application-level persistent IDs.

For the MVP:

- Scope persistent object IDs to individual recordings.
- Maintain mappings between SAM tracking IDs and MNEMOS IDs.
- Preserve model identifiers for debugging.
- Do not merge objects solely because they share the same category.
- Prefer conservative identity association.

Cross-video object re-identification is outside the initial MVP.

Design interfaces so appearance embeddings and more advanced identity matching can be introduced later.

---

## 8. Video Processing

Video processing should occur outside the HTTP request lifecycle.

Recommended flow:

1. Validate upload.
2. Persist video metadata.
3. Store media.
4. Create processing job.
5. Return video ID.
6. Process asynchronously.
7. Persist observations and memory.
8. Update processing status.

### Processing Status

Use explicit states:

- `queued`
- `discovering` (Muse Spark names the objects to track; skipped when the uploader names them)
- `tracking` (SAM runs once per object; the stage note reports `n/m tracked`)
- `building_memory`
- `analyzing_scene` (spatial relationships)
- `completed`
- `failed`

These are stored on the processing job (`stage`, `stage_detail`) and returned by `GET /videos/{id}`. A stage is recorded only when that work actually starts.

Status updates must reflect actual processing progress.

Do not generate fake processing completion states.

### Job Reliability

Processing runs in-process through FastAPI background tasks. This is the intended design for this project: it runs locally, and a job in flight is lost if the backend restarts (re-upload to retry). Cloud deployment and a durable queue are out of scope (`docs/decisions/0001-local-only-scope.md`); keep `ProcessingDispatcher` as the only thing the service layer knows about so one could be added.

Do not hold a web request open while waiting for long-running inference.

Keep file access behind `ObjectStorage`, with a configurable local storage path.

---

## 10. Python Coding Conventions

- Use Python type hints.
- Use async functions for asynchronous I/O.
- Avoid blocking the event loop with video decoding or synchronous network operations.
- Use dependency injection where it improves testability.
- Use Pydantic models for external data validation.
- Prefer small, focused functions.
- Avoid mutable global application state.
- Use explicit exception handling.
- Use structured logging.
- Keep configuration centralized.
- Avoid circular imports.
- Do not use wildcard imports.
- Avoid unnecessary inheritance hierarchies.

Use FastAPI lifespan management for shared external connections.

Close database and API clients during application shutdown.

---

## 11. Configuration

Use `pydantic-settings` for configuration management.

All sensitive values must come from environment variables.

Example variables:

```env
MODEL_API_KEY=
META_API_BASE_URL=
SAM_MODEL=
MUSE_MODEL=

NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=

MEDIA_STORAGE_PATH=
FRONTEND_ORIGIN=
```

These represent configuration fields, not confirmed environment variable requirements of the Meta SDK.

Never hardcode credentials.

Never expose secrets in logs.

Maintain `backend/.env.example`.

---

## 12. Error Handling and Observability

Use Python's logging module or an existing structured logging implementation.

Log meaningful processing events:

- Video upload accepted.
- Processing started.
- Model inference started/completed.
- Model parsing completed.
- Observations persisted.
- Graph update completed.
- Reasoning request completed.
- Processing failed.

Include video IDs, job IDs, and relevant timestamps.

Avoid logging API credentials, full model payloads containing sensitive information, or unnecessary video contents.

Use clear exception categories for:

- Invalid video input.
- Model API failures.
- Model parsing failures.
- Database failures.
- Processing failures.
- Unsupported reasoning requests.

---

## 13. Testing

Use pytest.

Prioritize tests for:

### SAM Parser

- Single-object response.
- Multiple-object response.
- Empty detection response.
- Malformed response.
- Multiple frames and tracking IDs.

### Temporal Memory

- Object registration.
- Observation persistence.
- Relationship creation.
- Historical relationship retrieval.
- Validity interval handling.
- Duplicate event prevention.

### Event Detection

- Object appearance.
- Object disappearance from view.
- Relationship change.
- Temporary detection loss.
- Uncertain observations.

### Reasoning

- Intent extraction.
- Graph query selection.
- Evidence retrieval.
- Unsupported questions.
- Insufficient evidence.

Use mocked model clients and stored response fixtures.

Do not require live Meta API access for unit tests.

Keep integration tests separate from unit tests.

Run the relevant test suite before declaring a feature complete.

---

## 14. Local Run Guidelines

The backend runs locally; cloud deployment is out of scope.

Requirements:

- Everything configurable through environment variables, documented in `backend/.env.example`. Defaults must work for a fresh clone against `docker-compose.yml`.
- No hardcoded development URLs.
- CORS limited to the origins in `FRONTEND_ORIGINS`.
- Startup health endpoint (`/health`).
- Graceful shutdown that closes database and API clients.
- Credentials only from the environment; never committed or logged.

External programs the backend needs: `ffmpeg` and `ffprobe` on `PATH`. The README lists them as prerequisites.

The backend must stay usable without the frontend (every capability is reachable through the HTTP API and the scripts in `backend/scripts`).

---