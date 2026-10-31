# Video ingestion and processing pipeline

```text
POST /api/v1/videos -> VideoIngestionService -> ObjectStorage (files) + Postgres (Video, ProcessingJob)
                                             -> ProcessingDispatcher.dispatch_video_processing(video_id, job_id)
                                                      |  (returns immediately, HTTP 202)
                                                      v
                          workers.video_worker.process_video_job -> VideoProcessingService
                              SamClient -> VideoProcessingResult -> Postgres (TrackedObject, Observation)
                                                                 -> GraphWriter (Neo4j)
```

Layers: `api` -> `services` -> `repositories` / integration protocols. Services depend only on
the protocols `ObjectStorage`, `SamClient`, `GraphWriter`, `ProcessingDispatcher`.

## Status model

`Video`: uploaded -> queued -> processing -> completed | failed.
`ProcessingJob`: pending -> running -> completed | failed (`error_message` set on failure).
QUEUED is committed before dispatch so a fast worker cannot be overwritten.

## Asynchronous processing

`ProcessingDispatcher` is the only thing the service layer knows about. The local
implementation (`BackgroundTasksDispatcher`) runs `process_video_job` via FastAPI
`BackgroundTasks` after the response is sent. Jobs do **not** survive a process restart.
To move to Google Cloud Pub/Sub: add a dispatcher that publishes `{video_id, job_id}`, and
have a subscriber call `process_video_job(container, video_id, job_id)`. No service change.
Processing is idempotent per video (existing tracked objects/observations are replaced; the
graph write uses MERGE on stable IDs).

## SAM integration

`SamClient.process_video(path) -> VideoProcessingResult` (`integrations/meta/sam_models.py`).
`sam_parser.parse_sam_artifacts` converts an experiment output directory
(`metadata.json`, `observations.json`, `tracking_summary.json`) using the existing
`ObservationTransformer`. Implementations:

- `MockSamClient` (`SAM_BACKEND=mock`, default): replays `backend/fixtures/sam_sample` for any video.
- `ScriptSamClient` (`SAM_BACKEND=script`): runs `scripts/test_sam_video.py` in a subprocess
  with `SAM_CONCEPT`, then parses the directory it reports. Not exercised in unit tests
  (needs live API); the script itself is unchanged.

## Neo4j

`Neo4jGraphWriter` wraps the existing `Neo4jMemoryRepository`: `(Video)-[:HAS_OBJECT]->(Object)`,
`(Object)-[:HAS_OBSERVATION]->(Observation)`, `(Video)-[:CONTAINS]->(Observation)`. Only facts
present in SAM output are written; events come from the deterministic detector and spatial relations from `spatial-memory.md`.
`NEO4J_ENABLED=false` swaps in `NullGraphWriter`. When enabled, startup fails fast if Neo4j is unreachable.
