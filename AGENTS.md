# MNEMOS — Agent Development Instructions

## 1. Project Overview

MNEMOS is a spatiotemporal visual memory system that enables AI systems to remember, retrieve, and reason about changes occurring in the physical world.

**Tagline:** Giving AI a memory of the physical world.

Traditional visual AI applications primarily focus on interpreting individual images, current observations, or short video sequences.

MNEMOS aims to provide persistent visual memory by maintaining a temporal representation of objects, their states, their spatial relationships, and how those relationships evolve over time.

The system transforms visual observations into a temporal knowledge graph that can be queried using natural language.

### Core Concept

MNEMOS is built around four fundamental capabilities:

1. **Perception:** Identify and track objects within visual observations.
2. **Scene Understanding:** Determine meaningful spatial relationships between observed objects.
3. **Memory:** Preserve object identities, observations, relationships, and events across time.
4. **Reasoning:** Retrieve historical information and produce evidence-grounded answers.

The key distinction is that MNEMOS should not simply describe what is visible in the current frame.

It should enable queries such as:

- What changed in this room over the last hour?
- Where was the laptop last observed?
- Which objects were on the desk before the notebook appeared?
- When did the coffee mug disappear from view?
- How did the relationships between objects evolve over time?

All responses must be grounded in stored observations and available evidence.

---

## 2. Hackathon Context

MNEMOS is being developed for the Meta Global AI Developer Hackathon 2026.

### Important Dates

- October 31, 2026: Target completion of the backend processing and reasoning pipeline.
- November 1, 2026: Target completion of frontend/backend integration.
- November 2, 2026: Feature-complete working prototype and feature freeze.
- November 3, 2026: Fresh-clone run verification, demo recording, and documentation.
- November 4, 2026: Submission preparation and final verification.
- November 5, 2026, 07:30 IST: Official submission deadline.

### Required Deliverables

The final submission must include:

1. A public GitHub repository.
2. A demonstration video of no more than three minutes (hosted on YouTube).
3. Written answers on the submission form: a project description, how Meta products were used, and why Meta's models matter to the solution.

The submission form does not ask for a hosted application. MNEMOS is therefore built to run locally from a fresh clone; cloud deployment is out of scope (see `docs/decisions/0001-local-only-scope.md`). A reviewer must be able to follow `README.md` and get the full pipeline running.

Draft submission text and the demo script are in `docs/specifications/submission.md`.

### Development Constraints

Development time is limited.

Prioritize delivering a complete, functional vertical slice over adding features that cannot be demonstrated reliably.

Every implementation decision should contribute directly to the working prototype.

Do not introduce unnecessary abstractions, infrastructure, dependencies, or architectural complexity.

After the feature freeze, prioritize reliability, integration, local run reproducibility, and documentation over additional features.

---

## 3. Technology Stack

### Backend

- Python 3.12+
- FastAPI
- Pydantic v2
- uv for dependency management
- Neo4j
- Neo4j Python driver
- OpenCV and FFmpeg
- Meta Model API
- pytest

### AI Models

**Meta SAM 3.1**

Responsible for object segmentation and tracking.

**Meta Muse Spark**

Responsible for scene understanding, semantic relationship extraction, query interpretation, and evidence-grounded reasoning.

Model availability, request formats, and response schemas must be verified against the actual API.

Do not assume models support capabilities that have not been tested.

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Flow for temporal knowledge graph visualization

Existing frontend libraries and components should be reused wherever appropriate.

### Database

Neo4j serves as the primary temporal knowledge graph database.

### Running locally

The project runs on a developer machine: Postgres and Neo4j through `backend/docker-compose.yml`, the FastAPI backend with `uvicorn`, and the frontend with Vite. FFmpeg and FFprobe must be installed.

Cloud deployment, container images for the apps, managed databases, object storage and message queues are out of scope. Keep the existing seams (`ObjectStorage`, `ProcessingDispatcher`) so they could be added later, but do not build them now.

Frontend and backend remain separate applications that communicate only through the documented HTTP API; do not couple them through shared files or a shared origin.

---

## 4. Repository Structure

MNEMOS is a monorepo containing:

```text
mnemos/
├── backend/
│   ├── src/
│   ├── tests/
│   ├── scripts/
│   ├── pyproject.toml
│   └── docker-compose.yml
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── specifications/
│   └── api/
│
├── AGENTS.md
├── README.md
└── .gitignore
```

The backend and frontend are separate applications that talk over the documented HTTP API.

Backend-specific instructions are defined in `backend/AGENTS.md`.

Frontend-specific instructions are defined in `frontend/AGENTS.md`.

---

## 5. Development Methodology

Use an incremental, vertical-slice development approach.

Prioritize this sequence:

1. Video input and SAM processing.
2. Structured object observations.
3. Neo4j persistence.
4. Temporal relationship construction.
5. Event detection.
6. Graph retrieval.
7. Muse Spark reasoning.
8. Frontend integration.
9. Local packaging, testing, and demo preparation.

Each stage must produce a verifiable result.

Avoid implementing disconnected components that cannot be integrated or tested.

### Feature Implementation Guidelines

Before implementing a feature:

1. Read the relevant architecture documentation.
2. Identify affected components.
3. Review existing interfaces and conventions.
4. Define or confirm input/output contracts.
5. Implement the smallest functional version.
6. Add relevant tests.
7. Run available validation commands.
8. Update documentation when necessary.

Avoid unrelated refactoring during feature implementation.

---

## 6. Coding Standards

- Write readable, maintainable code.
- Prefer explicit behavior over unnecessary abstractions.
- Follow existing project conventions.
- Use meaningful names.
- Keep components modular.
- Do not duplicate business logic.
- Avoid premature optimization.
- Handle errors explicitly.
- Validate external inputs and model outputs.
- Do not introduce speculative features.

Comments should explain complex decisions or non-obvious behavior.

Avoid comments that merely repeat what the code already communicates.

---

## 7. Testing Expectations

Prioritize automated tests for critical behavior.

Important areas include:

- SAM response parsing.
- Object tracking and identity association.
- Temporal graph updates.
- Historical relationship retrieval.
- Event generation.
- Reasoning query interpretation.
- Evidence validation.

Use saved model responses as test fixtures whenever possible.

Do not make real model API calls in ordinary unit tests.

Test integrations separately.

Ensure that historical graph queries return the expected state at specific timestamps.

---

## 8. Security and Configuration

Never commit anything.

Use `.env.example` files to document required configuration.

Never expose backend credentials through frontend environment variables.

Validate uploaded file types and sizes.

Prevent arbitrary file-path access through API parameters.

Do not allow model-generated queries to execute unrestricted database operations.

---

## 9. Documentation

The `docs/` directory is the architectural source of truth.

### Documentation Responsibilities

`docs/architecture/`

Describes system components, processing flows, and data models.

`docs/decisions/`

Contains Architecture Decision Records explaining important design choices.

`docs/specifications/`

Contains implementation specifications and acceptance criteria.

`docs/api/`

Contains frontend/backend API contracts.

Before making significant architectural changes, review the existing documentation.

When implementation changes invalidate documentation, update the relevant files.

Avoid creating unnecessary documents that duplicate existing information.

---

## 10. Git Workflow

The `main` branch should remain stable and runnable from a fresh clone.

Use short-lived feature branches for substantial changes.

Suggested naming:

- `feat/sam-video-processing`
- `feat/temporal-memory`
- `feat/muse-reasoning`
- `feat/frontend-integration`
- `fix/object-tracking`

Use clear commit messages.

Avoid committing generated outputs, temporary media, credentials, or large test artifacts unless intentionally required for the demo.

Keep pull requests focused.

---

## 11. MVP Scope

- Video upload and processing.
- SAM segmentation and tracking.
- Persistent object observations within a recording.
- Temporal knowledge graph construction.
- Historical graph retrieval.
- Basic event detection.
- Natural-language querying through Muse Spark.
- Evidence-linked answers.
- Interactive frontend integration.
- Reproducible local setup (README, `.env.example`, compose file) and demo assets.