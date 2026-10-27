# MNEMOS frontend

Interactive prototype of the MNEMOS spatiotemporal visual memory platform. Everything runs on local mock data; there is no backend, AI inference, auth or database.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck + production build
```

Stack: React, TypeScript (strict), Vite, Tailwind CSS v4, Radix primitives (shadcn-style `components/ui`), Lucide, React Flow, React Router, TanStack Query.

## Layout

- `src/mocks` – the 30 s office-desk scenario (objects, observations, relationships, events, evidence, canned answers).
- `src/services` – async service layer returning mock data. Each method documents the proposed `/api/v1/...` endpoint it will map to. Set `VITE_API_BASE_URL` (see `.env.example`) and swap the bodies for `apiFetch` calls.
- `src/hooks/useTimeline.ts` – the single source of truth for playback time; `ExplorerContext` adds shared selection (object / event / evidence) on top.
- `src/hooks/useMemoryGraph.ts` – temporal graph view (`validFrom <= t < validTo`) plus highlight state.
- `src/components/{video,graph,timeline,chat}` – the Memory Explorer panels.

## Prototype honesty

- Uploads stay in the browser (object URLs). Processing is a labeled, deterministic simulation; uploads get no detections, events or graph.
- The Office Desk Demo has no bundled video, so a labeled scene illustration stands in for it.
- "Ask MNEMOS" answers a fixed set of questions from mock data and says so for anything else. No LLM is called.
