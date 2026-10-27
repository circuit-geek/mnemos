import type { GraphRelationship } from "@/types";

/**
 * Full relationship history. Seeking never mutates this list: the graph only
 * filters it by `validFrom <= t < validTo`.
 */
export const relationships: GraphRelationship[] = [
  {
    id: "rel-laptop-on-desk",
    sourceId: "obj-laptop",
    targetId: "obj-desk",
    type: "ON",
    validFrom: 0,
    validTo: null,
    evidenceId: "ev-002",
  },
  {
    id: "rel-mug-on-desk",
    sourceId: "obj-mug",
    targetId: "obj-desk",
    type: "ON",
    validFrom: 0,
    validTo: 12,
    evidenceId: "ev-003",
  },
  {
    id: "rel-desk-in-office",
    sourceId: "obj-desk",
    targetId: "obj-office",
    type: "INSIDE",
    validFrom: 0,
    validTo: null,
    evidenceId: "ev-004",
  },
  {
    id: "rel-chair-next-to-desk",
    sourceId: "obj-chair",
    targetId: "obj-desk",
    type: "NEXT_TO",
    validFrom: 0,
    validTo: null,
    evidenceId: "ev-005",
  },
  {
    id: "rel-notebook-on-desk",
    sourceId: "obj-notebook",
    targetId: "obj-desk",
    type: "ON",
    validFrom: 20,
    validTo: null,
    evidenceId: "ev-009",
  },
];
