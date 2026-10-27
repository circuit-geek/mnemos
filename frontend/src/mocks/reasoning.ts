import type { AskResponse, EvidenceReference } from "@/types";
import { events, evidence } from "./events";
import { formatTime } from "@/lib/utils";

export const suggestedQuestions: string[] = [
  "What changed in this scene?",
  "Where was the coffee mug last seen?",
  "Which objects were on the desk initially?",
  "What happened between 00:10 and 00:25?",
];

export const UNSUPPORTED_ANSWER =
  "This is a prototype, and the current demo supports a limited set of questions. Try one of the suggested questions instead. Answers here come from predefined mock memory data, not a live AI model.";

function ev(...ids: string[]): EvidenceReference[] {
  return ids
    .map((id) => evidence.find((e) => e.id === id))
    .filter((e): e is EvidenceReference => e !== undefined);
}

function respond(answer: string, evidenceIds: string[]): AskResponse {
  const items = ev(...evidenceIds);
  return {
    answer,
    supported: true,
    evidence: items,
    referencedObjectIds: [...new Set(items.flatMap((e) => e.objectIds))],
  };
}

const norm = (q: string) => q.toLowerCase().replace(/[^a-z0-9: ]/g, " ").replace(/\s+/g, " ").trim();

function parseClock(s: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(s);
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

function answerChanged(): AskResponse {
  return respond(
    "Two changes were recorded between 00:00 and 00:30. The coffee mug stopped being visible on the desk at 00:12, so its ON relationship with the desk became inactive. At 00:20 a notebook appeared on the desk and a new ON relationship was created. The laptop stayed on the desk throughout. The mug's absence is a visibility observation, not proof that it was physically removed.",
    ["ev-006", "ev-007", "ev-008", "ev-009", "ev-010"],
  );
}

function answerMugLastSeen(): AskResponse {
  return respond(
    "The coffee mug was last seen on the desk, through 00:12 (ON relationship valid 00:00–00:12). It was no longer visible at 00:12 and still not visible at 00:30. The recording does not show where it went. Not being visible is not proof that it was moved.",
    ["ev-003", "ev-006", "ev-010"],
  );
}

function answerInitial(): AskResponse {
  return respond(
    "At 00:00 the laptop and the coffee mug were both on the desk. The desk itself was inside the office, and a chair stood next to it (not on it).",
    ["ev-002", "ev-003", "ev-004", "ev-005"],
  );
}

function answerRange(from: number, to: number): AskResponse {
  const inRange = events.filter((e) => e.timestamp >= from && e.timestamp <= to);
  if (inRange.length === 0) {
    return {
      answer: `No memory events were recorded between ${formatTime(from)} and ${formatTime(to)}.`,
      supported: true,
      evidence: [],
      referencedObjectIds: [],
    };
  }
  const lines = inRange.map((e) => `${formatTime(e.timestamp)} — ${e.description}`);
  return respond(
    `Between ${formatTime(from)} and ${formatTime(to)}, ${inRange.length} events were recorded: ${lines.join("; ")}.`,
    inRange.map((e) => e.evidenceId),
  );
}

/**
 * Deterministic matcher for the supported demo questions. Returns null for
 * anything else; callers must not invent an answer in that case.
 */
export function matchQuestion(question: string): AskResponse | null {
  const q = norm(question);

  const range = /between (\d{1,2}:\d{2}) and (\d{1,2}:\d{2})/.exec(q);
  if (range) {
    const from = parseClock(range[1] ?? "");
    const to = parseClock(range[2] ?? "");
    if (from !== null && to !== null && from <= to) return answerRange(from, to);
  }
  if (/what changed/.test(q)) return answerChanged();
  if (/mug/.test(q) && /(last seen|where)/.test(q)) return answerMugLastSeen();
  if (/initially|at the start|in the beginning/.test(q) && /desk/.test(q))
    return answerInitial();
  return null;
}
