/**
 * Domain types for MNEMOS. All timestamps are offsets in seconds from the
 * start of the recording. Shapes are intended to map 1:1 onto future FastAPI
 * (Pydantic) response models.
 */

export type ProcessingStatus = "processing" | "ready" | "failed";

export type ProcessingStageId =
  | "uploaded"
  | "perception"
  | "tracking"
  | "memory"
  | "ready";

export interface ProcessingStage {
  id: ProcessingStageId;
  label: string;
  description: string;
}

/** Progress of a (simulated) processing run. */
export interface ProcessingJob {
  id: string;
  videoId: string;
  status: ProcessingStatus;
  currentStage: ProcessingStageId;
  /** 0–100 overall progress. */
  progress: number;
  /** True while the pipeline is a browser-only demo simulation. */
  simulated: boolean;
  startedAt: string;
}

export type MediaKind = "scene-illustration" | "object-url";

export interface VideoRecord {
  id: string;
  title: string;
  description?: string;
  /** Seconds. */
  duration: number;
  status: ProcessingStatus;
  uploadedAt: string; // ISO 8601
  objectCount: number;
  eventCount: number;
  /** "scene-illustration" = bundled placeholder; "object-url" = a real local file. */
  mediaKind: MediaKind;
  /** Present only when a real video file is attached (blob: URL). */
  videoUrl?: string;
  /** True when the record is mock/demo data rather than a real analysis. */
  isDemo: boolean;
}

/** Normalised bounding box: all values 0–1 relative to the video frame. */
export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type ObjectCategory = "object" | "location";

export interface TrackedObject {
  id: string;
  label: string;
  category: ObjectCategory;
  firstObserved: number;
  lastObserved: number;
  /** Optional short description for the inspector. */
  note?: string;
}

export type Visibility = "visible" | "not_visible";

export interface ObjectObservation {
  id: string;
  objectId: string;
  timestamp: number;
  boundingBox: BoundingBox | null;
  visibility: Visibility;
  evidenceId: string;
}

export interface GraphNode {
  id: string;
  label: string;
  category: ObjectCategory;
  /** Whether the object is observed as visible at the queried timestamp. */
  visible: boolean;
}

export type RelationshipType =
  | "ON"
  | "NEXT_TO"
  | "INSIDE"
  | "NEAR"
  | "CONTAINS"
  | "HOLDING";

export interface GraphRelationship {
  id: string;
  sourceId: string;
  targetId: string;
  type: RelationshipType;
  validFrom: number;
  /** null = still valid at the end of the recording. */
  validTo: number | null;
  evidenceId: string;
}

export type MemoryEventType =
  | "object_appeared"
  | "object_disappeared"
  | "object_moved"
  | "relationship_changed";

export interface MemoryEvent {
  id: string;
  timestamp: number;
  type: MemoryEventType;
  description: string;
  objectIds: string[];
  relationshipIds: string[];
  evidenceId: string;
}

export interface EvidenceReference {
  id: string;
  timestamp: number;
  objectIds: string[];
  eventId?: string;
  relationshipIds?: string[];
  caption: string;
}

export type ReasoningRole = "user" | "assistant";

export interface ReasoningMessage {
  id: string;
  role: ReasoningRole;
  content: string;
  createdAt: string;
  /** Marks assistant replies for queries the prototype doesn't support. */
  unsupported?: boolean;
  error?: boolean;
  evidence?: EvidenceReference[];
  referencedObjectIds?: string[];
}

export interface AskResponse {
  answer: string;
  supported: boolean;
  evidence: EvidenceReference[];
  referencedObjectIds: string[];
}

/** Graph snapshot returned for `GET /videos/{id}/graph?timestamp=`. */
export interface GraphSnapshot {
  timestamp: number;
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  /** Observations of every object at the queried timestamp. */
  observations: ObjectObservation[];
}

export interface MemoryData {
  objects: TrackedObject[];
  /** Full history; never mutated by seeking. */
  relationships: GraphRelationship[];
  observations: ObjectObservation[];
  events: MemoryEvent[];
  evidence: EvidenceReference[];
}

/** What the explorer is currently highlighting (shared across panels). */
export interface Selection {
  objectId: string | null;
  eventId: string | null;
  evidenceId: string | null;
}
