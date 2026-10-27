import type { VideoRecord } from "@/types";
import { DEMO_VIDEO_ID } from "./objects";

export const demoVideos: VideoRecord[] = [
  {
    id: DEMO_VIDEO_ID,
    title: "Office Desk Demo",
    description:
      "Sample 30-second office desk scenario with mock memory data. No video file is bundled; a labeled scene illustration stands in for the recording.",
    duration: 30,
    status: "ready",
    uploadedAt: "2026-10-20T09:30:00Z",
    objectCount: 6,
    eventCount: 5,
    mediaKind: "scene-illustration",
    isDemo: true,
  },
];
