import { mapBox, type Rect } from "@/lib/geometry";
import { cn } from "@/lib/utils";
import type { BoundingBox } from "@/types";

export interface Detection {
  objectId: string;
  label: string;
  box: BoundingBox;
}

interface DetectionOverlayProps {
  content: Rect;
  detections: Detection[];
  selectedObjectId: string | null;
  /** Objects tied to the highlighted event / evidence. */
  focusObjectIds: ReadonlySet<string>;
  onSelect: (objectId: string) => void;
}

export function DetectionOverlay({
  content,
  detections,
  selectedObjectId,
  focusObjectIds,
  onSelect,
}: DetectionOverlayProps) {
  return (
    <>
      {detections.map((d) => {
        const r = mapBox(d.box, content);
        const selected = d.objectId === selectedObjectId;
        const focused = focusObjectIds.has(d.objectId);
        return (
          <button
            key={d.objectId}
            type="button"
            onClick={() => onSelect(d.objectId)}
            aria-pressed={selected}
            aria-label={`${d.label} detection`}
            className={cn(
              "pointer-events-auto absolute rounded-sm border transition-[border-color,background-color] duration-150",
              selected
                ? "z-10 border-2 border-accent bg-accent/15"
                : focused
                  ? "z-10 border-2 border-warning bg-warning/10"
                  : "border-white/70 hover:border-accent hover:bg-accent/10",
            )}
            style={{ left: r.left, top: r.top, width: r.width, height: r.height }}
          >
            <span
              className={cn(
                "absolute -top-px left-[-1px] -translate-y-full whitespace-nowrap rounded-t-sm px-1.5 py-0.5 text-[11px] font-medium leading-none",
                selected
                  ? "bg-accent text-accent-fg"
                  : focused
                    ? "bg-warning text-black"
                    : "bg-black/70 text-white",
              )}
            >
              {d.label}
            </span>
          </button>
        );
      })}
    </>
  );
}
