/**
 * Domain types for MNEMOS. All timestamps are offsets in seconds from the
 * start of the recording. Shapes are intended to map 1:1 onto future FastAPI
 * (Pydantic) response models.
 */

export type ProcessingStatus = "processing" | "ready" | "failed";

/** Mirrors the backend job stage; each is reported only when that work actually starts. */
export type ProcessingStageId =
  | "queued"
  | "discovering"
  | "tracking"
  | "building_memory"
  | "analyzing_scene"
  | "completed"
  | "failed";

export interface ProcessingStage {
  id: ProcessingStageId;
  label: string;
  description: string;
}

/** Progress of a real processing run, derived from the stage the backend reports. */
export interface ProcessingJob {
  id: string;
  videoId: string;
  status: ProcessingStatus;
  currentStage: ProcessingStageId;
  /** Backend note for the stage, e.g. "2/4 tracked: mug, pen, notebook". */
  detail: string | null;
  /** 0–100, by stage reached (not a time estimate). */
  progress: number;
  error: string | null;
}

export interface VideoRecord {
  id: string;
  title: string;
  description?: string;
  /** Seconds. */
  duration: number;
  status: ProcessingStatus;
  uploadedAt: string; // ISO 8601
  /** Tracked objects found; null while unknown. */
  objectCount: number | null;
  /** Pixel size of the source frames; needed to normalise detection boxes. */
  width: number | null;
  height: number | null;
  /** What the uploader asked to track; empty means the objects were discovered automatically. */
  requestedConcepts: string[];
  /** What the pipeline tracked (requested by the uploader or discovered). */
  trackedConcepts: string[];
  /** Playable original video served by the backend. */
  videoUrl: string;
  /** A frame from the video, for cards. */
  thumbnailUrl: string;
  job: ProcessingJob | null;
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
  /** The video frame at `timestamp`, served by the backend, when available. */
  frameUrl?: string;
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
  /** The backend found too little evidence in memory to answer. */
  unsupported?: boolean;
  /** How the question was interpreted, e.g. "RELATIONSHIPS · mug". */
  intent?: string;
  error?: boolean;
  evidence?: EvidenceReference[];
  referencedObjectIds?: string[];
}

export interface AskResponse {
  answer: string;
  /** False when memory held too little evidence to answer. */
  supported: boolean;
  intent: string | null;
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
