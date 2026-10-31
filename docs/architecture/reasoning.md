# Reasoning (CLI MVP)

Question → Muse Spark intent (`QueryIntent`, validated) → deterministic repository
calls → numbered evidence (`O1`, `E1`, `B1`…) → Muse Spark answer → validation.

- Model: `muse-spark-1.3` (override with `MUSE_MODEL`), called through the
  OpenAI-compatible Responses API at `https://api.meta.ai/v1`. Verified live:
  both `responses` and `chat.completions` work and return JSON when asked.
- Intents: `LAST_SEEN`, `CHANGES`, `OBJECT_HISTORY`, `SCENE_AT_TIME`,
  `RELATIONSHIPS`, `UNSUPPORTED`. The model never writes Cypher; each intent maps
  to fixed repository methods in `backend/reasoning/retrieval.py`.
- `RELATIONSHIPS` retrieves stored spatial relations (see `spatial-memory.md`); `UNSUPPORTED` returns an explicit insufficient-evidence
  answer (no relationships are stored yet). A missing object label or time is
  reported without calling the model for an answer.
- An answer that cites no retrieved evidence ID is withheld; unknown cited IDs are dropped.
- `NO_LONGER_VISIBLE` is treated as detection loss, never proof of disappearance.

## Run

```bash
cd backend
uv run python scripts/ask_memory.py --video-id mug "When did the mug disappear?"
uv run python scripts/ask_memory.py --video-id mug        # interactive
```

Flags: `--verbose` (show interpreted intent), `--json`, `--model`. Reads
`backend/.env` (`META_API_KEY`, Neo4j settings).
