import { Check, Loader2, MinusCircle, XCircle } from "lucide-react";
import { PROCESSING_STAGES } from "@/services/videoService";
import { cn } from "@/lib/utils";
import type { ProcessingJob } from "@/types";

/**
 * Live view of the backend pipeline. Steps are checked off only when the backend reports
 * having moved past them; "Finding objects" is shown as skipped when the uploader named the objects.
 */
export function ProcessingProgress({
  job,
  title,
  skippedDiscovery = false,
  className,
}: {
  job: ProcessingJob;
  title: string;
  skippedDiscovery?: boolean;
  className?: string;
}) {
  const failed = job.status === "failed";
  const finished = job.status === "ready";
  const currentIndex = Math.max(
    PROCESSING_STAGES.findIndex((s) => s.id === job.currentStage),
    0,
  );
  return (
    <section
      aria-label={`Processing ${title}`}
      className={cn("fade-in rounded-xl border border-line bg-surface p-4", className)}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="truncate text-sm font-medium">{title}</h3>
        <span className="ml-auto text-xs tabular-nums text-muted">{job.progress}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={job.progress}
        aria-valuemin={0}
        aria-valuemax={100}
        className="mb-4 h-1.5 overflow-hidden rounded-full bg-elevated"
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-500", failed ? "bg-warning" : "bg-accent")}
          style={{ width: `${failed ? Math.max(job.progress, 4) : job.progress}%` }}
        />
      </div>
      <ol className="flex flex-col gap-1.5">
        {PROCESSING_STAGES.map((stage, i) => {
          const skipped = stage.id === "discovering" && skippedDiscovery && i < currentIndex + 1;
          const done = !skipped && (i < currentIndex || finished);
          const active = i === currentIndex && !finished && !failed && !skipped;
          const broke = failed && i === currentIndex;
          return (
            <li
              key={stage.id}
              aria-current={active ? "step" : undefined}
              className={cn(
                "flex items-start gap-2.5 rounded-lg border px-3 py-2 text-xs",
                done && "border-success/30 text-fg",
                active && "border-accent/40 bg-accent-soft text-fg",
                broke && "border-warning/40 bg-warning/5 text-fg",
                !done && !active && !broke && "border-line text-muted",
              )}
            >
              <span className="mt-0.5 shrink-0">
                {done ? (
                  <Check className="size-3.5 text-success" aria-label="Complete" />
                ) : skipped ? (
                  <MinusCircle className="size-3.5" aria-label="Skipped" />
                ) : broke ? (
                  <XCircle className="size-3.5 text-warning" aria-label="Failed" />
                ) : active ? (
                  <Loader2 className="size-3.5 animate-spin text-accent" aria-label="In progress" />
                ) : (
                  <span className="block size-3.5 rounded-full border border-line" />
                )}
              </span>
              <span className="min-w-0">
                <span className="font-medium">{stage.label}</span>
                <span className="block text-muted">
                  {skipped
                    ? "Skipped: you named the objects to track"
                    : active && job.detail
                      ? job.detail
                      : stage.description}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
      {failed && job.error && (
        <p role="alert" className="mt-3 break-words rounded-lg border border-warning/40 bg-warning/5 p-2.5 text-xs text-warning">
          {job.error}
        </p>
      )}
    </section>
  );
}
