# MNEMOS backend

See `docs/architecture/video-ingestion.md` for the ingestion pipeline design.

## Local development

```bash
cp .env.example .env            # set NEO4J_PASSWORD; NEO4J_ENABLED=true to use Neo4j
docker compose up -d postgres   # add `neo4j` if NEO4J_ENABLED=true
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload
uv run pytest
```

```bash
curl -F "file=@clip.mp4;type=video/mp4" localhost:8000/api/v1/videos   # 202 {video_id, job_id}
curl localhost:8000/api/v1/videos/<video_id>                           # status -> completed
curl localhost:8000/api/v1/videos/<video_id>/observations
```

With `SAM_BACKEND=mock` (default) any valid mp4/mov/webm is "processed" using fixture output.
