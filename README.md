# MNEMOS

**Giving AI a memory of the physical world.**

MNEMOS is a spatiotemporal visual memory system. It turns video into a temporal knowledge graph of objects, their spatial relationships and the events that happen to them, then answers natural-language questions about that history with evidence-linked answers.

Most visual AI interprets a single frame or a short clip. MNEMOS remembers, so you can ask:

- What changed in this room over the last hour?
- Where was the laptop last observed?
- Which objects were on the desk before the notebook appeared?
- When did the coffee mug disappear from view?

Built for the Meta Global AI Developer Hackathon 2026.

## How it works

| Capability | What it does | Powered by |
|---|---|---|
| Perception | Segments and tracks objects across frames | Meta SAM 3.1 |
| Scene understanding | Extracts spatial relations (`ON`, `NEXT_TO`, `NEAR`, `INSIDE`) from sampled frames | Meta Muse Spark |
| Memory | Stores objects, observations, relations and events with validity intervals | Neo4j + Postgres |
| Reasoning | Interprets a question, retrieves matching graph facts, answers citing evidence | Meta Muse Spark |

Every answer cites retrieved evidence (observations, events, relations) with a video frame. An answer that cites nothing is withheld, and the model never writes Cypher: each question intent maps to fixed, parameterised graph queries.

## Architecture

```mermaid
graph LR
  subgraph Frontend [Frontend: React + Vite]
    UI[Memory Explorer<br/>video, graph, timeline, chat]
  end

  subgraph Backend [Backend: FastAPI]
    API[REST API /api/v1]
    ING[Ingestion service]
    WRK[Background worker]
    PROC[Video processing]
    SCENE[Scene analyzer]
    MEM[Temporal memory<br/>transformer + event detector]
    REA[Reasoning service]
  end

  subgraph Stores
    PG[(Postgres<br/>videos, jobs, tracks)]
    FS[(Local file storage<br/>uploads)]
    N4J[(Neo4j<br/>temporal knowledge graph)]
  end

  subgraph Meta [Meta Model API]
    SAM[SAM 3.1]
    MUSE[Muse Spark]
  end

  UI -->|HTTP| API
  API --> ING --> FS
  ING --> PG
  ING --> WRK --> PROC
  PROC --> SAM
  PROC --> MEM --> N4J
  PROC --> SCENE --> MUSE
  SCENE --> N4J
  API --> REA
  REA --> MUSE
  REA --> N4J
```

### Repository layout

```text
backend/    FastAPI service: ingestion, SAM, temporal + spatial memory, reasoning
frontend/   React + TypeScript + Vite + Tailwind + React Flow explorer
docs/       Architecture, decisions, specifications and API contracts
```

The project runs locally; cloud deployment is out of scope ([ADR 0001](docs/decisions/0001-local-only-scope.md)). Frontend and backend are separate applications that only talk over the HTTP API. See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md) for component-specific notes.

### Backend modules (`backend/src/backend`)

| Module | Responsibility |
|---|---|
| `api/` | HTTP routes for videos and memory queries |
| `services/` | Upload, processing orchestration, queries |
| `workers/` | Background job dispatch (FastAPI `BackgroundTasks`) |
| `integrations/meta/` | SAM client, SAM output parser, Muse concept discovery |
| `integrations/neo4j/` | Graph writer |
| `memory/` | Observation transformer, event detection, Neo4j repository |
| `scene/` | Spatial relation extraction and validity intervals |
| `reasoning/` | Muse client, intent interpretation, retrieval, evidence validation |

### Graph model

```mermaid
graph LR
  V[Video] -->|HAS_OBJECT| O[Object]
  V -->|CONTAINS| B[Observation]
  O -->|HAS_OBSERVATION| B
  V -->|HAS_EVENT| E[Event]
  O -->|PARTICIPATED_IN| E
  E -->|DERIVED_FROM| B
  O -->|ON / NEXT_TO / NEAR / INSIDE<br/>valid_from_ms, valid_to_ms| O2[Object]
```

- Events: `APPEARED`, `MOVED`, `NO_LONGER_VISIBLE`. The last reports detection loss, not proof that the object physically left.
- Relations carry a validity interval (`valid_from_ms <= t < valid_to_ms`), so historical queries return the state at a given timestamp.

Details: [`docs/architecture/`](docs/architecture) and [`docs/api/backend-api.md`](docs/api/backend-api.md).

## Flow

### Upload and processing

```mermaid
sequenceDiagram
  actor User
  participant FE as Frontend
  participant API as FastAPI
  participant PG as Postgres
  participant W as Worker
  participant SAM as SAM 3.1
  participant MS as Muse Spark
  participant N4J as Neo4j

  User->>FE: Upload video (optional concepts)
  FE->>API: POST /api/v1/videos
  API->>PG: Save Video + ProcessingJob (queued)
  API-->>FE: 202 {video_id, job_id}
  API--)W: dispatch job (background)

  opt no concepts supplied
    W->>MS: Sampled frames: what objects are here?
    MS-->>W: Object names
  end
  loop each concept
    W->>SAM: Segment and track concept
    SAM-->>W: Masks, boxes, tracking IDs
  end
  W->>PG: Tracked objects + observations
  W->>N4J: Objects, observations, events
  loop sampled frames with 2+ objects
    W->>MS: Frame + visible objects
    MS-->>W: Verified spatial relations
  end
  W->>N4J: Relations with validity intervals
  W->>PG: Job completed

  loop until completed
    FE->>API: GET /api/v1/videos/{id}
    API-->>FE: status + stage
  end
  FE->>API: GET /api/v1/videos/{id}/memory
  API->>N4J: Full history
  API-->>FE: objects, observations, events, relationships
```

### Asking a question

```mermaid
sequenceDiagram
  actor User
  participant FE as Frontend
  participant API as FastAPI
  participant MS as Muse Spark
  participant N4J as Neo4j

  User->>FE: "When did the mug disappear?"
  FE->>API: POST /api/v1/videos/{id}/ask
  API->>MS: Interpret question
  MS-->>API: Validated intent (e.g. LAST_SEEN, mug)
  API->>N4J: Fixed repository queries for that intent
  N4J-->>API: Observations, events, relations
  API->>API: Number evidence (O1, E1, R1...)
  API->>MS: Question + numbered evidence
  MS-->>API: Answer citing evidence IDs
  API->>API: Drop unknown IDs, withhold uncited answers
  API-->>FE: answer + evidence with frame URLs
  FE-->>User: Answer, interpretation, evidence frames
```

## Running the project

### Prerequisites

- Python 3.13+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- Docker (for Postgres and Neo4j)
- FFmpeg and FFprobe on `PATH` (frame extraction and video metadata)
- A Meta Model API key for real SAM and Muse Spark runs. Not needed for the mock mode below.

### 1. Backend

```bash
cd backend
cp .env.example .env
docker compose up -d postgres neo4j
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload
```

The API is served at http://localhost:8000. Edit `backend/.env` first:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL. Defaults to the bundled compose database: `postgresql+asyncpg://mnemos:mnemos@localhost:5432/mnemos` |
| `NEO4J_ENABLED` | `true` to build and query the knowledge graph (required for memory and `ask` endpoints) |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | e.g. `bolt://localhost:7687`, `neo4j`, and the compose password (`NEO4J_PASSWORD`, default `mnemos_dev_password`) |
| `SAM_BACKEND` | `mock` replays saved fixtures for any video; `script` runs real SAM |
| `META_API_KEY` | Meta Model API key (SAM, Muse Spark) |
| `MUSE_MODEL` | Defaults to `muse-spark-1.3` |
| `SAM_MAX_CONCEPTS`, `SCENE_SAMPLE_INTERVAL_MS`, `SCENE_MIN_CONFIDENCE` | Tracking and scene-analysis tuning |
| `FRONTEND_ORIGINS` | CORS origins, default `http://localhost:5173` |

Quick API check:

```bash
curl -F "file=@clip.mp4;type=video/mp4" localhost:8000/api/v1/videos   # 202 {video_id, job_id}
curl localhost:8000/api/v1/videos/<video_id>                           # poll until completed
curl -X POST localhost:8000/api/v1/videos/<video_id>/ask \
  -H 'Content-Type: application/json' -d '{"question": "Where was the mug last seen?"}'
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env     # VITE_API_BASE_URL, default http://localhost:8000
npm install
npm run dev              # http://localhost:5173
```

Open the app, upload a video (optionally list objects to track, e.g. `mug, notebook`), watch processing, then explore the graph and timeline and ask questions in the sidebar.

### Modes

- **Demo without API keys:** `SAM_BACKEND=mock`, `NEO4J_ENABLED=true`. Any valid mp4/mov/webm is "processed" with fixture output. Muse Spark features (concept discovery, spatial relations, `ask`) still need `META_API_KEY`.
- **Full pipeline:** `SAM_BACKEND=script` and `META_API_KEY` set.

### CLI utilities

```bash
cd backend
# Ingest a saved SAM experiment into Neo4j
uv run python scripts/ingest_memory.py <experiment_dir> --video-id <id>
# Ask questions from the terminal (interactive if no question is given)
uv run python scripts/ask_memory.py --video-id <id> "When did the mug disappear?"
```

### Tests

```bash
cd backend && uv run pytest        # uses saved fixtures; no live model calls
cd frontend && npm run build       # typecheck + production build
```

## Known limits

- The API has no authentication and is meant for one local user; do not expose it to the internet.
- Uploaded videos are stored on local disk.
- Object identity is scoped to one recording and can split across long occlusions.
- Relation boundaries are accurate only to the scene sampling interval.
- Background jobs do not survive a backend restart.

## Docs

- [Video ingestion](docs/architecture/video-ingestion.md)
- [Temporal memory](docs/architecture/temporal-memory.md)
- [Spatial memory](docs/architecture/spatial-memory.md)
- [Reasoning](docs/architecture/reasoning.md)
- [Backend API](docs/api/backend-api.md)
- Decisions: [local-only scope](docs/decisions/0001-local-only-scope.md), [per-video concepts](docs/decisions/0002-per-video-concepts-and-discovery.md), [spatial relations](docs/decisions/0003-spatial-relations-verified-on-sampled-frames.md)
- [Demo video plan](docs/specifications/demo-videos.md) and [submission notes](docs/specifications/submission.md)
