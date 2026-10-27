import { useState } from "react";
import { Box, ChevronDown, Info, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

export function GraphLegend() {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-line bg-surface/95 text-xs shadow-sm backdrop-blur">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-muted hover:text-fg"
      >
        <Info className="size-3.5" aria-hidden /> Legend
        <ChevronDown className={cn("ml-auto size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <ul className="flex flex-col gap-1.5 border-t border-line px-2.5 py-2 text-muted">
          <li className="flex items-center gap-2">
            <Box className="size-3.5" aria-hidden /> Physical object
          </li>
          <li className="flex items-center gap-2">
            <MapPin className="size-3.5" aria-hidden /> Location (dashed)
          </li>
          <li className="flex items-center gap-2">
            <span className="size-3.5 rounded border-2 border-accent" aria-hidden /> Selected
          </li>
          <li className="flex items-center gap-2">
            <span className="size-3.5 rounded border-2 border-warning" aria-hidden /> Event highlight
          </li>
          <li className="flex items-center gap-2">
            <span className="inline-block w-3.5 border-t-2 border-muted" aria-hidden /> Active relationship
          </li>
          <li className="flex items-center gap-2">
            <span className="inline-block w-3.5 border-t-2 border-dashed border-warning" aria-hidden /> Ended (shown
            with its event)
          </li>
          <li className="flex items-center gap-2 opacity-60">
            <span className="size-3.5 rounded border border-line bg-surface" aria-hidden /> Faded: not visible
          </li>
          <li className="pt-1 text-[10px] leading-relaxed">
            Types: ON · NEXT_TO · INSIDE · NEAR · CONTAINS · HOLDING
          </li>
        </ul>
      )}
    </div>
  );
}
