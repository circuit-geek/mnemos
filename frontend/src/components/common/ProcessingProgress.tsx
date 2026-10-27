import { Check, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PROCESSING_STAGES } from "@/services/videoService";
import { cn } from "@/lib/utils";
import type { ProcessingJob } from "@/types";

export function ProcessingProgress({ job, title }: { job: ProcessingJob; title: string }) {
  const currentIndex = PROCESSING_STAGES.findIndex((s) => s.id === job.currentStage);
  const finished = job.status === "ready";
  return (
    <section
      aria-label={`Processing ${title}`}
      className="fade-in rounded-xl border border-line bg-surface p-4"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="truncate text-sm font-medium">{title}</h3>
        <Badge tone="warning">Demo · simulated processing</Badge>
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
          className="h-full rounded-full bg-accent transition-[width] duration-200"
          style={{ width: `${job.progress}%` }}
        />
      </div>
      <ol className="grid gap-2 sm:grid-cols-5">
        {PROCESSING_STAGES.map((stage, i) => {
          const done = i < currentIndex || finished;
          const active = i === currentIndex && !finished;
          return (
            <li
              key={stage.id}
              aria-current={active ? "step" : undefined}
              className={cn(
                "flex items-start gap-2 rounded-lg border px-3 py-2 text-xs",
                done && "border-success/30 text-fg",
                active && "border-accent/40 bg-accent-soft text-fg",
                !done && !active && "border-line text-muted",
              )}
            >
              <span className="mt-0.5 shrink-0">
                {done ? (
                  <Check className="size-3.5 text-success" aria-label="Complete" />
                ) : active ? (
                  <Loader2 className="size-3.5 animate-spin text-accent" aria-label="In progress" />
                ) : (
                  <span className="block size-3.5 rounded-full border border-line" />
                )}
              </span>
              <span className="font-medium">{stage.label}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-xs text-muted">
        This run is a front-end simulation. The file stays in your browser and nothing is analyzed.
      </p>
    </section>
  );
}
