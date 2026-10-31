import { ApiError, apiFetch, frameUrl, videoMediaUrl } from "@/lib/api";
import type {
  ProcessingJob,
  ProcessingStage,
  ProcessingStageId,
  ProcessingStatus,
  VideoRecord,
} from "@/types";

export const ACCEPTED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
export const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".webm"];

/** The pipeline in order. `discovering` is skipped when the uploader names the objects. */
export const PROCESSING_STAGES: (ProcessingStage & { id: ProcessingStageId })[] = [
  { id: "queued", label: "Uploaded", description: "Stored and waiting for a worker" },
  { id: "discovering", label: "Finding objects", description: "Muse Spark looks at frames to name what to track" },
  { id: "tracking", label: "Tracking objects", description: "SAM 3.1 segments and tracks each object" },
  { id: "building_memory", label: "Building memory", description: "Observations, events and the temporal graph" },
  { id: "analyzing_scene", label: "Spatial relationships", description: "Muse Spark verifies what is on / next to what" },
  { id: "completed", label: "Ready", description: "Open in Memory Explorer" },
];

interface ApiJob {
  id: string;
  status: string;
  stage: string | null;
  stage_detail: string | null;
  error_message: string | null;
}

interface ApiVideo {
  id: string;
  original_filename: string;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  object_count: number | null;
  status: string;
  requested_concepts: string[] | null;
  tracked_concepts: string[] | null;
  created_at: string;
  processing_job: ApiJob | null;
}

function toStatus(status: string): ProcessingStatus {
  if (status === "completed") return "ready";
  if (status === "failed") return "failed";
  return "processing";
}

function toJob(video: ApiVideo): ProcessingJob | null {
  const job = video.processing_job;
  if (!job) return null;
  const status = toStatus(video.status);
  const stage = (
    status === "ready" ? "completed" : status === "failed" ? "failed" : (job.stage ?? "queued")
  ) as ProcessingStageId;
  const index = PROCESSING_STAGES.findIndex((s) => s.id === stage);
  return {
    id: job.id,
    videoId: video.id,
    status,
    currentStage: stage,
    detail: job.stage_detail,
    progress: status === "ready" ? 100 : Math.round((Math.max(index, 0) / (PROCESSING_STAGES.length - 1)) * 100),
    error: job.error_message,
  };
}

function toVideo(v: ApiVideo): VideoRecord {
  return {
    id: v.id,
    title: v.original_filename.replace(/\.[^.]+$/, ""),
    duration: v.duration_seconds ?? 0,
    status: toStatus(v.status),
    uploadedAt: v.created_at,
    objectCount: v.object_count,
    width: v.width,
    height: v.height,
    requestedConcepts: v.requested_concepts ?? [],
    trackedConcepts: v.tracked_concepts ?? [],
    videoUrl: videoMediaUrl(v.id),
    thumbnailUrl: frameUrl(v.id, 500),
    job: toJob(v),
  };
}

export function isAcceptedVideo(file: File): boolean {
  const name = file.name.toLowerCase();
  return (
    ACCEPTED_VIDEO_TYPES.includes(file.type) ||
    ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))
  );
}

export const videoService = {
  /** GET /api/v1/videos */
  async listVideos(): Promise<VideoRecord[]> {
    return (await apiFetch<ApiVideo[]>("/videos")).map(toVideo);
  },

  /** GET /api/v1/videos/{videoId} */
  async getVideo(videoId: string): Promise<VideoRecord> {
    return toVideo(await apiFetch<ApiVideo>(`/videos/${encodeURIComponent(videoId)}`));
  },

  /**
   * POST /api/v1/videos (multipart). `concepts` is a comma-separated list of objects to
   * track; leave it empty to let the backend discover them from the video.
   */
  async uploadVideo(file: File, concepts = ""): Promise<string> {
    if (!isAcceptedVideo(file)) {
      throw new ApiError("Unsupported file type. Use MP4, MOV or WebM.", 415);
    }
    const form = new FormData();
    form.append("file", file);
    if (concepts.trim()) form.append("concepts", concepts.trim());
    const res = await apiFetch<{ video_id: string }>("/videos", { method: "POST", body: form });
    return res.video_id;
  },
};
