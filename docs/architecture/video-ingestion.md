# Video ingestion and processing pipeline

```text
POST /api/v1/videos (file, optional concepts)
  -> VideoIngestionService -> ObjectStorage (file) + Postgres (Video, ProcessingJob)
  -> ProcessingDispatcher.dispatch_video_processing(video_id, job_id)   (returns at once, HTTP 202)
        v
  workers.video_worker.process_video_job -> VideoProcessingService
     discovering   Muse Spark names the objects to track (skipped if the uploader named them)
     tracking      SamClient: one SAM run per object, tracks merged -> VideoProcessingResult
     building_memory  Postgres (TrackedObject, Observation) + GraphWriter (Neo4j objects,
                      observations, events)
     analyzing_scene  SceneAnalyzer (Muse Spark on sampled frames) -> spatial relations -> Neo4j
     completed
```

Layers: `api` -> `services` -> `repositories` / integration protocols. Services depend only on
the protocols `ObjectStorage`, `SamClient`, `GraphWriter`, `ProcessingDispatcher`.

## Upload validation and de-duplication

Content type must be mp4, mov or webm, the container magic bytes must match, the file must be
non-empty and within `MAX_UPLOAD_BYTES` (500 MB). The optional `concepts` form field is a
comma-separated list (max 8 short plain names, validated in `core/concepts.py`); invalid input
returns 400 before anything is stored.

The SHA-256 of the bytes is stored on the video. An upload whose hash and requested concepts match a video that is completed or still in progress returns that video (`reused: true`, HTTP 200); failed videos are never reused. This makes re-uploading a demo clip instant and avoids paying for the same analysis twice.

## Status model

`Video`: uploaded -> queued -> processing -> completed | failed.
`ProcessingJob.status`: pending -> running -> completed | failed (`error_message` on failure).
`ProcessingJob.stage` / `stage_detail` hold the stage actually reached (`queued`, `discovering`,
`tracking`, `building_memory`, `analyzing_scene`, `completed`, `failed`) and a short note such as
`2/4 tracked: mug, pen, notebook, phone`. A stage is committed only when that work starts, so
the UI shows real progress. The progress callback is serialised with a lock because SAM runs
overlap and share one session.

## Identity linking

SAM gives an object that left view and returned a new tracking ID, so one mug could become two. After tracking, `integrations/meta/identity.link_split_tracks` merges same-label tracks only when it is unambiguous: they never overlap in time, the gap is at most 8 s, and no other track of that label is visible during the gap. The merged track keeps the first ID; the gap becomes a `NO_LONGER_VISIBLE` interval instead of a disappearance plus a new object, and the merge is logged and recorded in the object's attributes (`linked_tracking_ids`). When anything is ambiguous (two mugs, a long absence) the tracks stay separate.

## Frame timestamps

The SAM result carries the timestamp of every source frame, because observations refer to frames by number. Event detection indexes that list, so it must contain every frame, not only those with detections.

## Per-video concepts

What to track is decided per video, never globally:

1. The upload's `concepts` field, stored as `Video.requested_concepts`, wins.
2. Otherwise `ConceptDiscoverer` (`integrations/meta/concept_discovery.py`) samples
   `SAM_DISCOVERY_FRAMES` frames across the video, asks Muse Spark for object names, then cleans
   them (lowercase, dedupe, drop surfaces and body parts, cap at `SAM_MAX_CONCEPTS`).
3. If discovery fails or returns nothing, SAM falls back to `SAM_CONCEPT` (`object`) and logs a warning.

The concepts actually run are saved as `Video.tracked_concepts`. See `spatial-memory.md`.

## Asynchronous processing

`ProcessingDispatcher` is the only thing the service layer knows about. The implementation
(`BackgroundTasksDispatcher`) runs `process_video_job` via FastAPI `BackgroundTasks` after the
response is sent. A job in flight does **not** survive a backend restart; re-upload to retry.
This is deliberate: the project runs locally and cloud deployment, queues and object storage
are out of scope (`docs/decisions/0001-local-only-scope.md`). The seam stays so a durable
dispatcher could be added without touching the services.
Processing is idempotent per video: existing tracked objects and observations are replaced and
graph writes use MERGE on stable IDs; spatial relations are replaced per video.

## SAM integration

`SamClient.process_video(path, concepts, progress) -> VideoProcessingResult`
(`integrations/meta/sam_models.py`). `sam_parser.parse_sam_artifacts` converts a SAM experiment
output directory (`metadata.json`, `observations.json`, `tracking_summary.json`) using the
`ObservationTransformer`.

- `MockSamClient` (`SAM_BACKEND=mock`): replays `backend/fixtures/sam_sample` for any video.
- `ScriptSamClient` (`SAM_BACKEND=script`): runs `scripts/test_sam_video.py` in a subprocess
  once per concept (at most 3 at a time), passing `--concept=<name>`, then parses the directory
  it reports. A concept with no detections yields no tracks and is not an error; if every
  concept fails the job fails. Tracking IDs are only unique within one run, so they are
  prefixed (`mug-0`, `pen-0`) when several concepts are merged. Not exercised in unit tests
  (needs the live API).

The result also carries the frame width/height, stored on `Video` so the UI can normalise boxes.

## Neo4j

`Neo4jGraphWriter` wraps `Neo4jMemoryRepository`: `(Video)-[:HAS_OBJECT]->(Object)`,
`(Object)-[:HAS_OBSERVATION]->(Observation)`, `(Video)-[:CONTAINS]->(Observation)`, events from
the deterministic detector (`temporal-memory.md`) and spatial relations (`spatial-memory.md`).
`NEO4J_ENABLED=false` swaps in `NullGraphWriter` (no memory, graph or `ask` endpoints).
When enabled, startup fails fast if Neo4j is unreachable.

## Restarts and timeouts

Jobs run in-process, so on startup `services/recovery.fail_interrupted_jobs` marks any video or job left unfinished by a previous process as failed ("Interrupted by a backend restart... Upload the video again") instead of leaving the UI spinning. Each SAM run (`SAM_TIMEOUT_SECONDS`, default 600) and each Muse call (`MUSE_TIMEOUT_SECONDS`, default 90) has a timeout that fails the job with a clear message.

## Deleting a video

`DELETE /videos/{id}` removes the graph subgraph (observations, events, objects, relations, video node), the relational rows, and the stored file. It refuses while the video is still being processed.

## Failure policy

SAM or storage errors fail the job (`stage=failed`, `error_message` set). Scene analysis is an
enrichment: if it fails the video still completes with its temporal memory and the failure is
logged.

## Media

`GET /videos/{id}/media` serves the stored upload with HTTP range support;
`GET /videos/{id}/frames/{timestamp_ms}` extracts one JPEG with `ffmpeg`. Neither accepts a
file path, only a video ID and a timestamp. `ffmpeg` and `ffprobe` must be on `PATH`.
