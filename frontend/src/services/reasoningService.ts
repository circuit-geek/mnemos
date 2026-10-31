import { apiFetch, absoluteUrl } from "@/lib/api";
import type { AskResponse, EvidenceReference, MemoryData, TrackedObject } from "@/types";

interface ApiEvidence {
  evidence_id: string;
  kind: string;
  timestamp_ms: number | null;
  text: string;
  graph_id: string | null;
  evidence_uri: string | null;
}

interface ApiAnswer {
  answer: string;
  sufficient_evidence: boolean;
  intent: {
    intent: string;
    object_label: string | null;
    relation_type: string | null;
    before_appearance_of: string | null;
  };
  evidence: ApiEvidence[];
}

let answerSeq = 0;

/**
 * Backend evidence points at graph items (object / event / observation / relationship).
 * Resolve them against the loaded memory so a click can highlight the right objects.
 */
export function mapAnswer(res: ApiAnswer, memory: MemoryData): AskResponse {
  const seq = ++answerSeq;
  const evidence: EvidenceReference[] = [];
  for (const e of res.evidence) {
    if (e.timestamp_ms === null) continue; // notes carry no moment to jump to
    const ref: EvidenceReference = {
      id: `answer-${seq}-${e.evidence_id}`,
      timestamp: e.timestamp_ms / 1000,
      caption: e.text,
      objectIds: [],
      frameUrl: e.evidence_uri ? absoluteUrl(e.evidence_uri) : undefined,
    };
    const graphId = e.graph_id;
    if (e.kind === "object" && graphId) ref.objectIds = [graphId];
    else if (e.kind === "observation" && graphId) {
      const obs = memory.observations.find((o) => o.id === graphId);
      if (obs) ref.objectIds = [obs.objectId];
    } else if (e.kind === "event" && graphId) {
      const event = memory.events.find((x) => x.id === graphId);
      if (event) Object.assign(ref, { objectIds: event.objectIds, eventId: event.id, relationshipIds: event.relationshipIds });
    } else if (e.kind === "relationship" && graphId) {
      const rel = memory.relationships.find((r) => r.id === graphId);
      if (rel) Object.assign(ref, { objectIds: [rel.sourceId, rel.targetId], relationshipIds: [rel.id] });
    }
    evidence.push(ref);
  }
  const { intent } = res;
  const focus = [intent.object_label, intent.relation_type, intent.before_appearance_of && `before ${intent.before_appearance_of}`]
    .filter(Boolean)
    .join(" · ");
  return {
    answer: res.answer,
    supported: res.sufficient_evidence,
    intent: focus ? `${intent.intent} · ${focus}` : intent.intent,
    evidence,
    referencedObjectIds: [...new Set(evidence.flatMap((e) => e.objectIds))],
  };
}

export const reasoningService = {
  /** Suggestions come from what was actually found in this video. */
  suggestedQuestions(objects: TrackedObject[]): string[] {
    const labels = [...new Set(objects.map((o) => o.label))];
    const questions = ["What changed in this video?"];
    if (labels[0]) questions.push(`Where was the ${labels[0]} last seen?`);
    if (labels[1]) questions.push(`What is next to the ${labels[1]}?`);
    else if (labels[0]) questions.push(`What is near the ${labels[0]}?`);
    if (labels.length > 1) questions.push(`What happened to the ${labels[labels.length - 1]}?`);
    questions.push("What happened between 5 and 10 seconds?");
    return questions;
  },

  /** POST /api/v1/videos/{videoId}/ask — answered by Muse Spark from the stored memory. */
  async ask(videoId: string, question: string, memory: MemoryData): Promise<AskResponse> {
    const res = await apiFetch<ApiAnswer>(`/videos/${encodeURIComponent(videoId)}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    return mapAnswer(res, memory);
  },
};
