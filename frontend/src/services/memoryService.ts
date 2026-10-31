import { apiFetch, frameUrl } from "@/lib/api";
import type {
  BoundingBox,
  EvidenceReference,
  GraphRelationship,
  GraphSnapshot,
  MemoryData,
  MemoryEvent,
  MemoryEventType,
  ObjectObservation,
  RelationshipType,
  VideoRecord,
} from "@/types";

/**
 * An object counts as visible only if it was detected this recently. Beyond that the
 * last detection is stale, so it is reported as not visible instead of being reused.
 */
export const VISIBLE_GAP_S = 0.5;

/* ---- backend response shapes (GET /videos/{id}/memory) ---- */

interface ApiBundle {
  objects: {
    object_id: string;
    label: string;
    first_seen_ms: number;
    last_seen_ms: number;
  }[];
  observations: {
    object_id: string;
    observation_id: string;
    timestamp_ms: number;
    bounding_box: number[];
  }[];
  events: {
    event_id: string;
    object_id: string;
    related_object_id: string | null;
    relationship_id: string | null;
    event_type: string;
    start_time_ms: number;
    description: string;
  }[];
  relationships: {
    relationship_id: string;
    subject_object_id: string;
    target_object_id: string;
    relation_type: string;
    valid_from_ms: number;
    valid_to_ms: number | null;
    evidence_timestamp_ms: number;
    reason: string | null;
  }[];
}

const EVENT_TYPES: Record<string, MemoryEventType> = {
  APPEARED: "object_appeared",
  MOVED: "object_moved",
  NO_LONGER_VISIBLE: "object_disappeared",
  RELATIONSHIP_STARTED: "relationship_changed",
  RELATIONSHIP_ENDED: "relationship_changed",
};

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** Backend boxes are pixel [left, top, right, bottom]; the UI uses 0–1 fractions of the frame. */
function normalise(box: number[], width: number | null, height: number | null): BoundingBox | null {
  if (!width || !height || box.length !== 4) return null;
  const [left, top, right, bottom] = box as [number, number, number, number];
  return {
    x: clamp01(left / width),
    y: clamp01(top / height),
    w: clamp01((right - left) / width),
    h: clamp01((bottom - top) / height),
  };
}

export function toMemoryData(video: VideoRecord, api: ApiBundle): MemoryData {
  const labels = new Map(api.objects.map((o) => [o.object_id, o.label]));
  const label = (id: string) => labels.get(id) ?? "object";

  const objects = api.objects.map((o) => ({
    id: o.object_id,
    label: o.label,
    category: "object" as const,
    firstObserved: o.first_seen_ms / 1000,
    lastObserved: o.last_seen_ms / 1000,
  }));

  const observations: ObjectObservation[] = api.observations.map((o) => ({
    id: o.observation_id,
    objectId: o.object_id,
    timestamp: o.timestamp_ms / 1000,
    boundingBox: normalise(o.bounding_box, video.width, video.height),
    visibility: "visible",
    evidenceId: o.observation_id,
  }));

  const relationships: GraphRelationship[] = api.relationships.map((r) => ({
    id: r.relationship_id,
    sourceId: r.subject_object_id,
    targetId: r.target_object_id,
    type: r.relation_type as RelationshipType,
    validFrom: r.valid_from_ms / 1000,
    validTo: r.valid_to_ms === null ? null : r.valid_to_ms / 1000,
    evidenceId: `evidence:${r.relationship_id}`,
  }));

  const events: MemoryEvent[] = api.events.map((e) => ({
    id: e.event_id,
    timestamp: e.start_time_ms / 1000,
    type: EVENT_TYPES[e.event_type] ?? "object_moved",
    description: e.description,
    objectIds: [e.object_id, ...(e.related_object_id ? [e.related_object_id] : [])],
    relationshipIds: e.relationship_id ? [e.relationship_id] : [],
    evidenceId: `evidence:${e.event_id}`,
  }));

  const evidence: EvidenceReference[] = [
    ...api.relationships.map((r) => ({
      id: `evidence:${r.relationship_id}`,
      timestamp: r.evidence_timestamp_ms / 1000,
      objectIds: [r.subject_object_id, r.target_object_id],
      relationshipIds: [r.relationship_id],
      caption: `${label(r.subject_object_id)} ${r.relation_type} ${label(r.target_object_id)}${r.reason ? ` — ${r.reason}` : ""}`,
      frameUrl: frameUrl(video.id, r.evidence_timestamp_ms),
    })),
    ...events.map((e) => ({
      id: e.evidenceId,
      timestamp: e.timestamp,
      objectIds: e.objectIds,
      eventId: e.id,
      relationshipIds: e.relationshipIds,
      caption: e.description,
      frameUrl: frameUrl(video.id, e.timestamp * 1000),
    })),
  ];

  return { objects, relationships, observations, events, evidence };
}

/** A relationship is active when validFrom <= t < validTo (null = open-ended). */
export function isRelationshipActive(rel: GraphRelationship, t: number): boolean {
  return rel.validFrom <= t && (rel.validTo === null || t < rel.validTo);
}

// Observations per object, sorted by time. Built once per observations array.
const indexCache = new WeakMap<ObjectObservation[], Map<string, ObjectObservation[]>>();

function indexOf(all: ObjectObservation[]): Map<string, ObjectObservation[]> {
  let index = indexCache.get(all);
  if (!index) {
    index = new Map();
    for (const o of all) {
      const list = index.get(o.objectId);
      if (list) list.push(o);
      else index.set(o.objectId, [o]);
    }
    for (const list of index.values()) list.sort((a, b) => a.timestamp - b.timestamp);
    indexCache.set(all, index);
  }
  return index;
}

/**
 * What the memory says about an object at `t`: null before it was first seen; a visible
 * observation if it was detected within VISIBLE_GAP_S; otherwise a not-visible marker
 * (no box) so a stale detection is never drawn.
 */
export function getObservationAt(
  all: ObjectObservation[],
  objectId: string,
  t: number,
): ObjectObservation | null {
  const list = indexOf(all).get(objectId);
  if (!list || list.length === 0 || list[0]!.timestamp > t) return null;
  let lo = 0;
  let hi = list.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (list[mid]!.timestamp <= t) lo = mid;
    else hi = mid - 1;
  }
  const latest = list[lo]!;
  if (t - latest.timestamp <= VISIBLE_GAP_S) return latest;
  return { ...latest, id: `${latest.id}~gap`, boundingBox: null, visibility: "not_visible" };
}

/** Pure temporal query over the full history; seeking never mutates `memory`. */
export function computeGraphSnapshot(memory: MemoryData, t: number): GraphSnapshot {
  const current: ObjectObservation[] = [];
  const nodes = memory.objects.flatMap((o) => {
    const obs = getObservationAt(memory.observations, o.id, t);
    if (!obs) return [];
    current.push(obs);
    return [{ id: o.id, label: o.label, category: o.category, visible: obs.visibility === "visible" }];
  });
  return {
    timestamp: t,
    nodes,
    relationships: memory.relationships.filter((r) => isRelationshipActive(r, t)),
    observations: current,
  };
}

export const memoryService = {
  /** GET /api/v1/videos/{videoId}/memory — objects, observations, events, relationships. */
  async getMemory(video: VideoRecord): Promise<MemoryData> {
    return toMemoryData(video, await apiFetch<ApiBundle>(`/videos/${encodeURIComponent(video.id)}/memory`));
  },
};
