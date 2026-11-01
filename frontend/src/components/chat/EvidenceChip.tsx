import { Clock } from "lucide-react";
import { FOCUS_WINDOW_S } from "@/hooks/useMemoryGraph";
import { getObservationAt } from "@/services/memoryService";
import { useExplorer } from "@/hooks/ExplorerContext";
import { cn, formatTime } from "@/lib/utils";
import type { EvidenceReference } from "@/types";

/** Clicking seeks the video, updates the graph, selects the object and highlights this item. */
export function EvidenceChip({ evidence }: { evidence: EvidenceReference }) {
  const { focusEvidence, selection, timeline, memory } = useExplorer();
  // Where the cited objects were in this frame (only if they were actually detected then).
  const boxes = evidence.objectIds.flatMap((id) => {
    const obs = getObservationAt(memory.observations, id, evidence.timestamp);
    const label = memory.objects.find((o) => o.id === id)?.label ?? "";
    return obs?.boundingBox ? [{ id, label, box: obs.boundingBox }] : [];
  });
  const active =
    selection.evidenceId === evidence.id &&
    Math.abs(timeline.currentTime - evidence.timestamp) <= FOCUS_WINDOW_S;
  return (
    <button
      type="button"
      onClick={() => focusEvidence(evidence)}
      aria-pressed={active}
      className={cn(
        "flex w-full items-start gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition-colors hover:border-accent/60",
        active ? "border-accent bg-accent-soft" : "border-line bg-surface",
      )}
    >
      {evidence.frameUrl && (
        <span className="relative block aspect-video w-28 shrink-0 overflow-hidden rounded-md border border-line bg-elevated">
          <img src={evidence.frameUrl} alt="" loading="lazy" className="size-full object-cover" />
          {boxes.map((b) => (
            <span
              key={b.id}
              title={b.label}
              className="absolute rounded-[2px] border-2 border-accent bg-accent/15"
              style={{ left: `${b.box.x * 100}%`, top: `${b.box.y * 100}%`, width: `${b.box.w * 100}%`, height: `${b.box.h * 100}%` }}
            />
          ))}
        </span>
      )}
      <span
        className={cn(
          "mt-px flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 font-semibold tabular-nums",
          active ? "bg-accent text-accent-fg" : "bg-elevated text-accent",
        )}
      >
        <Clock className="size-3" aria-hidden />
        {formatTime(evidence.timestamp)}
      </span>
      <span className="leading-snug text-muted">
        <span className={active ? "text-fg" : undefined}>{evidence.caption}</span>
      </span>
    </button>
  );
}
