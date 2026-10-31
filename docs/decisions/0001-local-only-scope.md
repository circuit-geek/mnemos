# 0001: Run locally; cloud deployment is out of scope

Status: accepted (2026-10-31)

## Context

Early plans (and the root `AGENTS.md`) assumed a publicly hosted application. The hackathon
submission form asks for a project description, a public GitHub repository, a demo video of at
most three minutes, and short answers about the use of Meta products. It does not ask for a live
application. Time before the November 5 deadline is limited.

## Decision

MNEMOS is built to run on a developer machine from a fresh clone: Postgres and Neo4j through
`backend/docker-compose.yml`, the FastAPI backend with `uvicorn`, the frontend with Vite. We do
not build cloud deployment, application container images, managed databases, object storage,
a message queue, hosting configuration, authentication or per-user quotas.

## Consequences

- Reviewers follow `README.md`. Defaults in `.env.example` must work against the compose file, and
  the README must list prerequisites (Python 3.13+, uv, Node, Docker, FFmpeg/FFprobe, a Meta API key).
- Uploaded videos live on local disk behind the `ObjectStorage` interface.
- Processing runs in-process (`BackgroundTasksDispatcher`); a job in flight is lost if the backend
  restarts. The API has no authentication and must not be exposed to the internet.
- The seams (`ObjectStorage`, `ProcessingDispatcher`, `SamClient`, `GraphWriter`) are kept, so
  cloud pieces can be added later without changing services.
- Time goes into the product instead: spatial reasoning, discovery quality, evidence, the
  explorer, tests, documentation and the demo.

## If deployment is revisited

Use a durable dispatcher (queue plus a worker) and an object-storage `ObjectStorage`
implementation, serve media through signed URLs, add authentication with per-user ownership and
quotas on upload and `ask` (they call paid Meta APIs), and cap instances and spend. Direct-to-storage
upload is needed for files above typical request-size limits.
