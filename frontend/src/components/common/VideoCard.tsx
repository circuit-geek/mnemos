import { Link } from "react-router-dom";
import { ArrowRight, Boxes, CalendarDays, Clock, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SceneIllustration } from "@/components/video/SceneIllustration";
import { StatusBadge } from "./StatusBadge";
import { formatDate, formatTime } from "@/lib/utils";
import type { VideoRecord } from "@/types";

const INITIAL_VISIBLE = new Set(["obj-laptop", "obj-mug", "obj-desk", "obj-chair"]);

function Thumbnail({ video }: { video: VideoRecord }) {
  if (video.mediaKind === "object-url" && video.videoUrl) {
    return (
      <video
        src={`${video.videoUrl}#t=0.1`}
        muted
        playsInline
        preload="metadata"
        className="size-full object-cover"
        aria-label={`Preview frame of ${video.title}`}
      />
    );
  }
  return (
    <>
      <SceneIllustration visibleObjectIds={INITIAL_VISIBLE} className="object-cover" />
      <Badge className="absolute left-2 top-2 bg-surface/90 backdrop-blur">
        Sample scene illustration
      </Badge>
    </>
  );
}

export function VideoCard({ video }: { video: VideoRecord }) {
  const ready = video.status === "ready";
  return (
    <article className="fade-in flex flex-col overflow-hidden rounded-xl border border-line bg-surface transition-colors hover:border-accent/40">
      <div className="relative aspect-video overflow-hidden border-b border-line bg-elevated">
        <Thumbnail video={video} />
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-semibold leading-snug">{video.title}</h3>
          <StatusBadge status={video.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-muted">
          <div className="flex items-center gap-1.5">
            <Clock className="size-3.5" aria-hidden />
            <dt className="sr-only">Duration</dt>
            <dd>{formatTime(video.duration)}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <CalendarDays className="size-3.5" aria-hidden />
            <dt className="sr-only">Uploaded</dt>
            <dd>{formatDate(video.uploadedAt)}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <Boxes className="size-3.5" aria-hidden />
            <dt className="sr-only">Detected objects</dt>
            <dd>{video.objectCount} objects</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="size-3.5" aria-hidden />
            <dt className="sr-only">Events</dt>
            <dd>{video.eventCount} events</dd>
          </div>
        </dl>
        {video.description && (
          <p className="text-xs leading-relaxed text-muted">{video.description}</p>
        )}
        <div className="mt-auto pt-1">
          {ready ? (
            <Button asChild variant="primary" size="sm" className="w-full">
              <Link to={`/explore/${video.id}`}>
                Open Explorer <ArrowRight className="size-4" />
              </Link>
            </Button>
          ) : (
            <Button variant="secondary" size="sm" className="w-full" disabled>
              Processing…
            </Button>
          )}
        </div>
      </div>
    </article>
  );
}
