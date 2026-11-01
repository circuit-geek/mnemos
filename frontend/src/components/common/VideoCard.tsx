import { Link } from "react-router-dom";
import { useState } from "react";
import { ArrowRight, Boxes, CalendarDays, Clock, ImageOff, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./StatusBadge";
import { formatDate, formatTime } from "@/lib/utils";
import type { VideoRecord } from "@/types";

export function VideoCard({
  video,
  onDelete,
  deleting = false,
}: {
  video: VideoRecord;
  onDelete?: (video: VideoRecord) => void;
  deleting?: boolean;
}) {
  const ready = video.status === "ready";
  const [thumbFailed, setThumbFailed] = useState(false);
  const stage = video.job?.currentStage;
  return (
    <article className="fade-in flex flex-col overflow-hidden rounded-xl border border-line bg-surface transition-colors hover:border-accent/40">
      <div className="relative aspect-video overflow-hidden border-b border-line bg-elevated">
        {thumbFailed ? (
          <div className="grid size-full place-items-center text-muted" role="img" aria-label="Preview unavailable">
            <ImageOff className="size-6" aria-hidden />
          </div>
        ) : (
          <img
            src={video.thumbnailUrl}
            alt={`Frame from ${video.title}`}
            loading="lazy"
            className="size-full object-cover"
            onError={() => setThumbFailed(true)}
          />
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="break-words text-base font-semibold leading-snug">{video.title}</h3>
          <StatusBadge status={video.status} />
        </div>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-muted">
          <div className="flex items-center gap-1.5">
            <Clock className="size-3.5" aria-hidden />
            <dt className="sr-only">Duration</dt>
            <dd>{ready ? formatTime(video.duration) : "—"}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <CalendarDays className="size-3.5" aria-hidden />
            <dt className="sr-only">Uploaded</dt>
            <dd>{formatDate(video.uploadedAt)}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <Boxes className="size-3.5" aria-hidden />
            <dt className="sr-only">Tracked objects</dt>
            <dd>{ready && video.objectCount !== null ? `${video.objectCount} tracked` : "—"}</dd>
          </div>
        </dl>
        {video.trackedConcepts.length > 0 && (
          <ul className="flex flex-wrap gap-1" aria-label="Tracked objects">
            {video.trackedConcepts.map((c) => (
              <li key={c}>
                <Badge>{c}</Badge>
              </li>
            ))}
          </ul>
        )}
        {video.status === "failed" && video.job?.error && (
          <p className="line-clamp-2 text-xs text-warning">{video.job.error}</p>
        )}
        <div className="mt-auto flex items-center gap-2 pt-1">
          {ready ? (
            <Button asChild variant="primary" size="sm" className="flex-1">
              <Link to={`/explore/${video.id}`}>
                Open Explorer <ArrowRight className="size-4" />
              </Link>
            </Button>
          ) : video.status === "failed" ? (
            <Button variant="secondary" size="sm" className="flex-1" disabled>
              Processing failed
            </Button>
          ) : (
            <Button asChild variant="secondary" size="sm" className="flex-1">
              <Link to={`/explore/${video.id}`}>
                Watch processing{stage && stage !== "queued" ? "" : "…"} <ArrowRight className="size-4" />
              </Link>
            </Button>
          )}
          {onDelete && video.status !== "processing" && (
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Delete ${video.title}`}
              disabled={deleting}
              onClick={() => onDelete(video)}
            >
              <Trash2 className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </article>
  );
}
