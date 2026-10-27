import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import type { TrackedObject } from "@/types";

interface ObjectChipsProps {
  objects: TrackedObject[];
  visibleIds: ReadonlySet<string>;
  observedIds: ReadonlySet<string>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ObjectChips({ objects, visibleIds, observedIds, selectedId, onSelect }: ObjectChipsProps) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Detected objects">
      {objects.map((o) => {
        const selected = o.id === selectedId;
        const visible = visibleIds.has(o.id);
        const observed = observedIds.has(o.id);
        return (
          <li key={o.id}>
            <button
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(o.id)}
              title={
                visible ? undefined : observed ? "Not visible at this time" : "Not observed yet at this time"
              }
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                selected
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-line bg-elevated text-fg hover:border-accent/50",
                !visible && !selected && "text-muted",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  visible ? "bg-success" : "border border-muted",
                )}
                aria-hidden
              />
              {o.label}
              {o.category === "location" && <span className="text-[10px] text-muted">location</span>}
              <span className="sr-only">{visible ? "(visible)" : "(not visible)"}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export function ObjectChipsSkeleton() {
  return (
    <div className="flex gap-2" aria-busy="true" aria-label="Loading detected objects">
      {[72, 96, 80, 60, 70].map((w) => (
        <Skeleton key={w} className="h-7 rounded-full" />
      ))}
    </div>
  );
}
