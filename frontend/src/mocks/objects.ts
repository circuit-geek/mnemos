import type {
  BoundingBox,
  ObjectObservation,
  TrackedObject,
  Visibility,
} from "@/types";

export const DEMO_VIDEO_ID = "vid-office-desk-demo";

export const objects: TrackedObject[] = [
  {
    id: "obj-office",
    label: "Office",
    category: "location",
    firstObserved: 0,
    lastObserved: 30,
    note: "The room containing the desk.",
  },
  {
    id: "obj-desk",
    label: "Desk",
    category: "object",
    firstObserved: 0,
    lastObserved: 30,
    note: "Work surface inside the office.",
  },
  {
    id: "obj-laptop",
    label: "Laptop",
    category: "object",
    firstObserved: 0,
    lastObserved: 30,
  },
  {
    id: "obj-mug",
    label: "Coffee Mug",
    category: "object",
    firstObserved: 0,
    lastObserved: 12,
    note: "Not visible after 00:12. Disappearance is a visibility observation, not proof it was removed.",
  },
  {
    id: "obj-notebook",
    label: "Notebook",
    category: "object",
    firstObserved: 20,
    lastObserved: 30,
  },
  {
    id: "obj-chair",
    label: "Chair",
    category: "object",
    firstObserved: 0,
    lastObserved: 30,
  },
];

/** Fixed node positions so the graph never reshuffles while seeking. */
export const graphLayout: Record<string, { x: number; y: number }> = {
  "obj-office": { x: 220, y: 0 },
  "obj-desk": { x: 220, y: 150 },
  "obj-laptop": { x: 20, y: 310 },
  "obj-mug": { x: 220, y: 330 },
  "obj-notebook": { x: 420, y: 310 },
  "obj-chair": { x: 440, y: 150 },
};

const box = (x: number, y: number, w: number, h: number): BoundingBox => ({
  x,
  y,
  w,
  h,
});

/** Bounding boxes on the 16:9 sample scene, normalised 0–1. */
export const sceneBoxes = {
  desk: box(0.06, 0.6, 0.68, 0.36),
  laptop: box(0.19, 0.3, 0.26, 0.31),
  mug: box(0.53, 0.45, 0.075, 0.16),
  notebook: box(0.45, 0.585, 0.17, 0.065),
  chair: box(0.78, 0.36, 0.17, 0.58),
} as const;

function obs(
  objectId: string,
  timestamp: number,
  visibility: Visibility,
  boundingBox: BoundingBox | null,
  evidenceId: string,
): ObjectObservation {
  return {
    id: `obs-${objectId.replace("obj-", "")}-${timestamp}`,
    objectId,
    timestamp,
    visibility,
    boundingBox,
    evidenceId,
  };
}

export const observations: ObjectObservation[] = [
  obs("obj-office", 0, "visible", null, "ev-004"),
  obs("obj-desk", 0, "visible", sceneBoxes.desk, "ev-004"),
  obs("obj-laptop", 0, "visible", sceneBoxes.laptop, "ev-002"),
  obs("obj-mug", 0, "visible", sceneBoxes.mug, "ev-003"),
  obs("obj-chair", 0, "visible", sceneBoxes.chair, "ev-005"),
  obs("obj-mug", 12, "not_visible", null, "ev-006"),
  obs("obj-notebook", 20, "visible", sceneBoxes.notebook, "ev-008"),
  obs("obj-office", 30, "visible", null, "ev-010"),
  obs("obj-desk", 30, "visible", sceneBoxes.desk, "ev-010"),
  obs("obj-laptop", 30, "visible", sceneBoxes.laptop, "ev-010"),
  obs("obj-mug", 30, "not_visible", null, "ev-010"),
  obs("obj-notebook", 30, "visible", sceneBoxes.notebook, "ev-010"),
  obs("obj-chair", 30, "visible", sceneBoxes.chair, "ev-010"),
];
