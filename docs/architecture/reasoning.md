# Reasoning

Question -> Muse Spark intent (`QueryIntent`, validated) -> deterministic repository
calls -> numbered evidence (`O1`, `E1`, `B1`, `R1`...) -> Muse Spark answer -> validation.

Served by `POST /api/v1/videos/{id}/ask` (see `docs/api/backend-api.md`) and by
`backend/scripts/ask_memory.py`.

- Model: `muse-spark-1.3` (override with `MUSE_MODEL`), called through the OpenAI-compatible
  Responses API at `https://api.meta.ai/v1`. Text and image input are both used (image input for
  concept discovery and spatial verification, see `spatial-memory.md`).
- Intents: `LAST_SEEN`, `CHANGES`, `OBJECT_HISTORY`, `SCENE_AT_TIME`, `RELATIONSHIPS`,
  `UNSUPPORTED`. The model never writes Cypher; each intent maps to fixed repository methods in
  `backend/reasoning/retrieval.py`.
- Beyond the intent, the interpreter fills optional fields: `object_label` (must be a known
  object), `time_seconds` or `start_seconds`/`end_seconds`, `relation_type`
  (`ON`/`NEXT_TO`/`NEAR`/`INSIDE`) and `before_appearance_of` ("before the notebook appeared"
  resolves to just before that object's first detection). Invalid values fail validation; unknown
  relation words mean "any relation".
- `RELATIONSHIPS` retrieves stored spatial relations; `SCENE_AT_TIME` also includes relations
  holding at that moment. Asking for `NEAR` also returns `NEXT_TO`. If the requested relation type
  has no match, a note plus the relations that were verified are returned so the answer can say
  "not ON, but NEXT_TO". Surfaces such as a desk are not tracked objects.
- `UNSUPPORTED` questions, a missing object label or time, and empty results return an explicit
  insufficient-evidence answer without asking the model to answer.
- An answer that cites no retrieved evidence ID is withheld; unknown cited IDs are dropped.
- `NO_LONGER_VISIBLE` is treated as detection loss, never proof of disappearance. Relation times
  are accurate only to the scene sampling interval; a relation not listed was not verified.

## Response

`{question, intent, answer, sufficient_evidence, evidence[]}`. Each evidence item has an ID,
kind (`object`, `event`, `observation`, `relationship`, `note`), a timestamp, text, the graph ID it
refers to, and a frame URL (`/api/v1/videos/{id}/frames/{ms}`), never a server path.

## Run from the terminal

```bash
cd backend
uv run python scripts/ask_memory.py --video-id <id> "When did the mug disappear?"
uv run python scripts/ask_memory.py --video-id <id>        # interactive
```

Flags: `--verbose` (show interpreted intent), `--json`, `--model`. Reads `backend/.env`
(`META_API_KEY`, Neo4j settings).
