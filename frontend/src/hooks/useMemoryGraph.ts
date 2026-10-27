import { useMemo } from "react";
import { computeGraphSnapshot, getObservationAt, isRelationshipActive } from "@/services/memoryService";
import type { GraphRelationship, GraphSnapshot, MemoryData, Selection } from "@/types";

/** Highlights from an event or evidence item stay visible only near its timestamp. */
export const FOCUS_WINDOW_S = 0.5;

export interface GraphFocus {
  objectIds: ReadonlySet<string>;
  relationshipIds: ReadonlySet<string>;
}

const NO_FOCUS: GraphFocus = { objectIds: new Set(), relationshipIds: new Set() };

/** The event/evidence currently being highlighted, if playback is still at its timestamp. */
export function resolveFocus(memory: MemoryData, selection: Selection, t: number): GraphFocus {
  const objectIds = new Set<string>();
  const relationshipIds = new Set<string>();
  const event = memory.events.find((e) => e.id === selection.eventId);
  const ev = memory.evidence.find((e) => e.id === selection.evidenceId);
  for (const item of [event, ev]) {
    if (!item || Math.abs(item.timestamp - t) > FOCUS_WINDOW_S) continue;
    item.objectIds.forEach((id) => objectIds.add(id));
    const rels = "relationshipIds" in item ? (item.relationshipIds ?? []) : [];
    rels.forEach((id) => relationshipIds.add(id));
  }
  return objectIds.size === 0 && relationshipIds.size === 0
    ? NO_FOCUS
    : { objectIds, relationshipIds };
}

export interface MemoryGraphView {
  snapshot: GraphSnapshot;
  focus: GraphFocus;
  /**
   * Inactive relationships tied to the highlighted event (e.g. the mug–desk ON
   * that just ended). Shown dashed as history; never removed from the data.
   */
  endedRelationships: GraphRelationship[];
}

export function useMemoryGraph(memory: MemoryData, t: number, selection: Selection): MemoryGraphView {
  // The snapshot only changes when an observation or relationship validity
  // changes, so key it on those to avoid rebuilding every playback tick.
  const key =
    memory.objects.map((o) => getObservationAt(memory.observations, o.id, t)?.id ?? "-").join("|") +
    "#" +
    memory.relationships.map((r) => (isRelationshipActive(r, t) ? 1 : 0)).join("");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const snapshot = useMemo(() => computeGraphSnapshot(memory, t), [memory, key]);

  const raw = resolveFocus(memory, selection, t);
  const focusKey = [...raw.objectIds].join(",") + "|" + [...raw.relationshipIds].join(",");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const focus = useMemo(() => raw, [focusKey]);
  const endedKey = memory.relationships
    .filter((r) => focus.relationshipIds.has(r.id) && !isRelationshipActive(r, t))
    .map((r) => r.id)
    .join(",");
  const endedRelationships = useMemo(
    () => memory.relationships.filter((r) => endedKey.split(",").includes(r.id)),
    [memory, endedKey],
  );
  return { snapshot, focus, endedRelationships };
}
