# Submission

Deadline: 2026-11-05 07:30 IST. The form asks for: a project description, a public GitHub
repository, a 3-minute demo video (YouTube), how Meta products were used, why Meta's models are
important to the solution, and optionally an X post for the Most Viral Track. No hosted app is
required (`docs/decisions/0001-local-only-scope.md`).

## Checklist

- [ ] Repository is public; no secrets in the tree or history (`backend/.env`, API keys).
- [ ] Large and local-only folders stay out: `backend/outputs/` (SAM experiment output, many GB),
      `backend/data/`, `backend/test_data/`, `frontend/node_modules`, `.idea/`.
- [ ] A fresh clone runs by following `README.md` only (compose, migrations, backend, frontend).
- [ ] `backend/.env.example` works against `docker-compose.yml`; the README says a Meta API key is needed.
- [ ] Demo clips a reviewer can use are committed somewhere small and tracked (for example `demo/`).
- [ ] `cd backend && uv run pytest` and `cd frontend && npm run build` pass.
- [ ] Demo video uploaded to YouTube (3 minutes at most) and the link works logged out.

## Demo video script (about 3:00)

Processing a clip takes 1-2 minutes, so pre-process the clips and cut or speed up the wait.

| Time | Show | Say |
|---|---|---|
| 0:00 | Title, then a frame of `scenario_2` | Visual AI describes a frame but forgets. MNEMOS gives AI a memory of the physical world. |
| 0:20 | Library: upload, leave "objects to track" empty | Upload; MNEMOS finds the objects itself (Muse Spark), or you can name them. |
| 0:35 | Live pipeline view | Finding objects, SAM tracking each, building memory, verifying spatial relations: real stages. |
| 0:55 | Explorer: video with boxes, graph, timeline | Detections, a temporal graph and events share one clock. |
| 1:15 | Scrub 0:00 to 0:18 | Notebook appears at 8 s, phone at 15 s; relations appear and end. Seeking back restores earlier states. |
| 1:45 | Ask "What is next to the notebook?" | Muse Spark answers only from stored memory; evidence cites relations and frames. |
| 2:05 | Click evidence | The video, graph and timeline jump to that moment. |
| 2:20 | Ask "Which objects were on the desk before the notebook appeared?" and an unanswerable question | Time-aware retrieval; it says when evidence is missing. |
| 2:40 | `scenario_1` (mug leaves and returns) briefly | Gaps are "no longer detected", not proof the object left. |
| 2:50 | Architecture slide | SAM 3.1 tracks; Muse Spark discovers, verifies relations, interprets and answers; Neo4j stores the graph. |

## Form answers (drafts)

Project description:

> Visual AI can describe what it sees in a frame, but it cannot remember what happened. MNEMOS
> gives AI a memory of the physical world. Upload a video and MNEMOS finds and tracks the objects
> in it, works out how they relate to each other (on, next to, near, inside), and turns the result
> into a temporal knowledge graph in Neo4j. You can scrub through time and watch the graph change,
> or ask in plain language: "What changed in this video?", "Where was the mug last seen?", "What is
> next to the notebook?", "What was in the scene before the notebook appeared?". Every answer is
> grounded in stored observations and cites evidence you can click to jump to the exact frame. When
> memory does not contain enough to answer, MNEMOS says so instead of guessing.

Use of Meta products:

> MNEMOS uses two Meta models through the Meta Model API. SAM 3.1 segments and tracks objects across
> the video, giving each a persistent identity and a bounding box on every frame. Muse Spark is used
> at four points: discovering which objects are worth tracking from frames sampled across the video;
> verifying spatial relationships between tracked objects on sampled frames; interpreting a
> natural-language question into a structured query; and writing the answer using only evidence
> retrieved from the graph, with citations validated before they are shown.

Why Meta's models are important:

> MNEMOS needs two capabilities working together. SAM 3.1's promptable segmentation and tracking turns
> raw video into stable object identities over time, which is the foundation of memory. Muse Spark's
> multimodal reasoning adds meaning: it reads frames to say how objects relate, understands free-form
> questions, and returns structured JSON we can validate. Both are reachable through one API, which
> kept the pipeline simple. Together they take us from "what is in this frame" to "what changed,
> where and when", with answers tied to visual evidence.

Keep claims to what the demo shows: object identity is scoped to one recording and can split across
long occlusions; relation times are accurate to the sampling interval.
