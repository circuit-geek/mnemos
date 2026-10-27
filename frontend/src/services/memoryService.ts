import { mockLatency } from "@/lib/api";
import { DEMO_VIDEO_ID, objects, observations } from "@/mocks/objects";
import { relationships } from "@/mocks/relationships";
import { events, evidence } from "@/mocks/events";
import type {
  GraphRelationship,
  GraphSnapshot,
  MemoryData,
  MemoryEvent,
  ObjectObservation,
  TrackedObject,
} from "@/types";

const EMPTY_MEMORY: MemoryData = {
  objects: [],
  relationships: [],
  observations: [],
  events: [],
  evidence: [],
};

/** A relationship is active when validFrom <= t < validTo (null = open-ended). */
export function isRelationshipActive(rel: GraphRelationship, t: number): boolean {
  return rel.validFrom <= t && (rel.validTo === null || t < rel.validTo);
}

/** Latest observation of an object at or before `t`, or null if never seen yet. */
export function getObservationAt(
  all: ObjectObservation[],
  objectId: string,
  t: number,
): ObjectObservation | null {
  let latest: ObjectObservation | null = null;
  for (const o of all) {
    if (o.objectId === objectId && o.timestamp <= t) {
      if (latest === null || o.timestamp >= latest.timestamp) latest = o;
    }
  }
  return latest;
}

/**
 * Pure temporal query. Mirrors the proposed
 * `GET /videos/{id}/graph?timestamp=` response so it can be swapped for the
 * backend later without touching callers.
 */
export function computeGraphSnapshot(memory: MemoryData, t: number): GraphSnapshot {
  const current: ObjectObservation[] = [];
  const nodes = memory.objects.flatMap((o) => {
    const obs = getObservationAt(memory.observations, o.id, t);
    if (!obs) return [];
    current.push(obs);
    return [
      {
        id: o.id,
        label: o.label,
        category: o.category,
        visible: obs.visibility === "visible",
      },
    ];
  });
  return {
    timestamp: t,
    nodes,
    relationships: memory.relationships.filter((r) => isRelationshipActive(r, t)),
    observations: current,
  };
}

export const memoryService = {
  /** GET /api/v1/videos/{videoId}/objects (plus observations, evidence & relationship history). */
  async getMemory(videoId: string): Promise<MemoryData> {
    const data: MemoryData =
      videoId === DEMO_VIDEO_ID
        ? { objects, relationships, observations, events, evidence }
        : EMPTY_MEMORY;
    return mockLatency(data, 280);
  },

  async getObjects(videoId: string): Promise<TrackedObject[]> {
    return (await this.getMemory(videoId)).objects;
  },

  /** GET /api/v1/videos/{videoId}/graph?timestamp=12 */
  async getGraph(videoId: string, timestamp: number): Promise<GraphSnapshot> {
    return computeGraphSnapshot(await this.getMemory(videoId), timestamp);
  },

  /** GET /api/v1/videos/{videoId}/events */
  async getEvents(videoId: string): Promise<MemoryEvent[]> {
    return (await this.getMemory(videoId)).events;
  },
};
