# MNEMOS backend

FastAPI service: video ingestion, SAM tracking, temporal and spatial memory in Neo4j, and
evidence-grounded reasoning with Muse Spark. Setup, configuration and the full run-through are in
the root [`README.md`](../README.md).

```bash
cp .env.example .env                       # add META_API_KEY; the rest works with the compose file
docker compose up -d postgres neo4j
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload   # http://localhost:8000
uv run pytest                              # saved fixtures; no live model calls
```

Requires `ffmpeg` and `ffprobe` on `PATH`. With `SAM_BACKEND=mock` any valid mp4/mov/webm is
"processed" using fixture output (Muse features still need `META_API_KEY`).

Design docs: `docs/architecture/` (ingestion, temporal memory, spatial memory, reasoning),
`docs/api/backend-api.md` (endpoints), `docs/decisions/` (why).
