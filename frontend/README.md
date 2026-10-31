# MNEMOS frontend

Web UI for the MNEMOS spatiotemporal visual memory platform. It talks to the FastAPI backend (`backend/`) for upload, processing progress, detections, the temporal graph and Muse Spark reasoning.

```bash
# backend first (see backend/README.md), then:
cp .env.example .env   # VITE_API_BASE_URL, default http://localhost:8000
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck + production build
```

Stack: React, TypeScript (strict), Vite, Tailwind CSS v4, Radix primitives (shadcn-style `components/ui`), Lucide, React Flow, React Router, TanStack Query.

## Layout

- `src/services` – the only code that calls the backend (`videoService`, `memoryService`, `reasoningService`). They map API responses to the domain types in `src/types`. Endpoints are listed in `docs/api/backend-api.md`.
- `src/lib/api.ts` – base URL (`VITE_API_BASE_URL`), typed fetch with error handling, media/frame URL helpers.
- `src/hooks/useTimeline.ts` – the single source of truth for playback time; `ExplorerContext` adds shared selection (object / event / evidence) on top.
- `src/hooks/useMemoryGraph.ts` – temporal graph view (`validFrom <= t < validTo`) plus highlight state. The explorer loads the full history once (`GET /videos/{id}/memory`) and derives every moment client-side, so seeking costs no requests.
- `src/components/{video,graph,timeline,chat}` – the Memory Explorer panels.

## How it behaves

- **Upload** sends the file (and optional comma-separated objects to track) to the backend, then opens the explorer, which shows the real pipeline stage while the original video plays. It switches to the results when the backend reports completion.
- **Detections** are drawn from stored observations. An object not detected within 0.5 s of the playhead is shown as not visible; a stale box is never reused.
- **Ask MNEMOS** shows the actual Muse Spark answer, how the question was interpreted, and its cited evidence with video frames. Failures are shown as errors; nothing falls back to canned answers.
