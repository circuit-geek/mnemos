import { mockLatency } from "@/lib/api";
import { demoVideos } from "@/mocks/videos";
import type {
  ProcessingJob,
  ProcessingStage,
  ProcessingStageId,
  VideoRecord,
} from "@/types";

export const ACCEPTED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
export const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".webm"];

export const PROCESSING_STAGES: ProcessingStage[] = [
  { id: "uploaded", label: "Video uploaded", description: "File received in your browser" },
  { id: "perception", label: "Visual perception", description: "Detect objects in frames" },
  { id: "tracking", label: "Object tracking", description: "Follow objects over time" },
  { id: "memory", label: "Memory construction", description: "Build the temporal graph" },
  { id: "ready", label: "Ready for exploration", description: "Open in Memory Explorer" },
];

/** Each of the four transitions takes this long, so a run is 6 s total. */
export const STAGE_DURATION_MS = 1500;

interface UploadEntry {
  video: VideoRecord;
  startedAtMs: number;
  startedAtIso: string;
}

// In-memory store for the prototype. Uploads live only for this page session.
const uploads: UploadEntry[] = [];

function jobFor(entry: UploadEntry, now: number): ProcessingJob {
  const elapsed = now - entry.startedAtMs;
  const done = elapsed >= STAGE_DURATION_MS * 4;
  const stageIndex = done ? 4 : Math.floor(elapsed / STAGE_DURATION_MS);
  const stage = PROCESSING_STAGES[stageIndex]?.id ?? "ready";
  return {
    id: `job-${entry.video.id}`,
    videoId: entry.video.id,
    status: done ? "ready" : "processing",
    currentStage: stage as ProcessingStageId,
    progress: Math.min(100, Math.round((elapsed / (STAGE_DURATION_MS * 4)) * 100)),
    simulated: true,
    startedAt: entry.startedAtIso,
  };
}

function resolved(entry: UploadEntry, now: number): VideoRecord {
  const job = jobFor(entry, now);
  return { ...entry.video, status: job.status };
}

function readDuration(url: string): Promise<number> {
  return new Promise((resolve) => {
    const el = document.createElement("video");
    el.preload = "metadata";
    el.onloadedmetadata = () => resolve(Number.isFinite(el.duration) ? el.duration : 0);
    el.onerror = () => resolve(0);
    el.src = url;
  });
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
    const now = Date.now();
    const mine = uploads.map((u) => resolved(u, now)).reverse();
    return mockLatency([...mine, ...demoVideos], 200);
  },

  /** GET /api/v1/videos/{videoId} */
  async getVideo(videoId: string): Promise<VideoRecord> {
    const now = Date.now();
    const upload = uploads.find((u) => u.video.id === videoId);
    const found = upload ? resolved(upload, now) : demoVideos.find((v) => v.id === videoId);
    if (!found) throw new Error("Recording not found");
    return mockLatency(found, 150);
  },

  /** Processing jobs for uploads in this session (derived from elapsed time). */
  async listJobs(): Promise<ProcessingJob[]> {
    const now = Date.now();
    return uploads.map((u) => jobFor(u, now));
  },

  /**
   * POST /api/v1/videos
   * Mock: keeps the file in the browser as an object URL and starts a
   * simulated, deterministic processing run. Nothing is uploaded or analyzed.
   */
  async uploadVideo(file: File): Promise<VideoRecord> {
    if (!isAcceptedVideo(file)) {
      throw new Error("Unsupported file type. Use MP4, MOV or WebM.");
    }
    const url = URL.createObjectURL(file);
    const duration = await readDuration(url);
    const now = Date.now();
    const video: VideoRecord = {
      id: `vid-upload-${now}`,
      title: file.name.replace(/\.[^.]+$/, ""),
      description: "Local file. Processing is simulated; no objects or events are detected.",
      duration,
      status: "processing",
      uploadedAt: new Date(now).toISOString(),
      objectCount: 0,
      eventCount: 0,
      mediaKind: "object-url",
      videoUrl: url,
      isDemo: true,
    };
    uploads.push({ video, startedAtMs: now, startedAtIso: video.uploadedAt });
    return video;
  },
};
