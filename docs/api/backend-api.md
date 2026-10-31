# Backend API (v1)

Base path `/api/v1`. Timestamps are milliseconds from the start of the recording unless noted.
Memory endpoints need `NEO4J_ENABLED=true`; `ask` also needs `META_API_KEY`. Otherwise they return 503.
CORS origins come from `FRONTEND_ORIGINS` (comma-separated).

| Method | Path | Purpose |
|---|---|---|
| POST | `/videos` | Upload (multipart `file`, optional `concepts`: comma-separated objects to track, e.g. `mug, notebook`; omit to let the model discover them per video; invalid names return 400). 202 `{video_id, job_id, status}`; processing runs in the background and builds temporal memory (objects, observations, events). |
| GET | `/videos` | Recent videos, newest first (`limit`), each with `object_count`, `width`/`height`, concepts and its latest job. |
| GET | `/videos/{id}` | Video and processing job status, plus `requested_concepts`, `tracked_concepts` and `width`/`height`. `processing_job.stage` is the stage actually reached (`queued`, `discovering`, `tracking`, `building_memory`, `analyzing_scene`, `completed`, `failed`) and `stage_detail` a short note (e.g. `2/4 tracked: mug, pen, notebook, phone`). Poll until `completed`. |
| GET | `/videos/{id}/media` | The original upload for playback; supports HTTP range requests. |
| GET | `/videos/{id}/memory` | Full history in one response: `objects`, all `observations` (pixel `bounding_box`), `events` and `relationships`. Relationship start/end appear as derived `RELATIONSHIP_STARTED` / `RELATIONSHIP_ENDED` events. The explorer derives any moment from this. |
| GET | `/videos/{id}/observations` | Relational observations (`limit`, `offset`). |
| POST | `/videos/{id}/ask` | Body `{question}`. Returns `{question, intent, answer, sufficient_evidence, evidence[]}`; `intent` shows how the question was interpreted (intent, object, relation type, time). Every answer cites retrieved evidence; see `docs/architecture/reasoning.md`. |
| GET | `/videos/{id}/objects` | Tracked objects in the graph. |
| GET | `/videos/{id}/objects/{object_id}/history` | Observations of one object, in time order. |
| GET | `/videos/{id}/events` | `APPEARED`, `MOVED`, `NO_LONGER_VISIBLE` events. |
| GET | `/videos/{id}/relationships?at_seconds=&object_id=` | Spatial relations (`ON`, `NEXT_TO`, `NEAR`, `INSIDE`) with `valid_from_ms`, `valid_to_ms` (exclusive, `null` = still holding when last verified) and an evidence frame URL. |
| GET | `/videos/{id}/graph?at_seconds=` | `{nodes, edges}` for React Flow; edges are `HAS_OBJECT`, `PARTICIPATED_IN` and the spatial relation types. With `at_seconds`, only objects and events known by that moment, with each object's latest observation. |
| GET | `/videos/{id}/frames/{timestamp_ms}` | JPEG frame of the stored video at that time (extracted with ffmpeg; takes no file paths). |

Evidence: every `evidence_uri` in `ask`, `history` and `graph` responses is a relative frame URL
(`/api/v1/videos/{id}/frames/{timestamp_ms}`) to prepend with the API base, never a server path.
It is `null` for evidence with no timestamp.

Errors: 400 invalid upload or concepts, 404 unknown video or no frame at that time, 413 file too large, 415 unsupported type, 422 invalid input, 502 model failure, 503 memory or reasoning not configured.

The API has no authentication; it is meant to run locally for one user (`docs/decisions/0001-local-only-scope.md`). Do not expose it to the internet as is.
`NO_LONGER_VISIBLE` means the tracker stopped detecting an object, not that it physically left.
