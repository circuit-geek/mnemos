import { useEffect, useRef } from "react";
import { Zap } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { EmptyState } from "@/components/common/EmptyState";
import { cn, formatTime } from "@/lib/utils";
import { EVENT_META } from "./eventMeta";

export function EventList() {
  const { memory, timeline, graph, selection, selectEvent } = useExplorer();
  const activeId = graph.focus.objectIds.size > 0 ? selection.eventId : null;
  const refs = useRef(new Map<string, HTMLLIElement>());

  useEffect(() => {
    if (!activeId) return;
    refs.current.get(activeId)?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }, [activeId]);

  if (memory.events.length === 0) {
    return (
      <EmptyState
        className="rounded-xl border border-line bg-surface py-5"
        icon={<Zap className="size-4" />}
        title="No memory events"
        description="Events appear here when objects appear, disappear, move or change relationships."
      />
    );
  }

  return (
    <section aria-label="Memory events">
      <ol className="flex gap-3 overflow-x-auto pb-2">
        {memory.events.map((e) => {
          const { Icon, label, text } = EVENT_META[e.type];
          const active = e.id === activeId;
          const future = e.timestamp > timeline.currentTime;
          return (
            <li
              key={e.id}
              ref={(el) => {
                if (el) refs.current.set(e.id, el);
                else refs.current.delete(e.id);
              }}
              className="shrink-0"
            >
              <button
                type="button"
                onClick={() => selectEvent(e)}
                aria-current={active ? "true" : undefined}
                className={cn(
                  "flex h-full w-60 flex-col gap-2 rounded-xl border bg-surface p-3 text-left transition-colors hover:border-accent/50",
                  active ? "border-accent bg-accent-soft" : "border-line",
                  future && !active && "opacity-60",
                )}
              >
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-semibold tabular-nums">{formatTime(e.timestamp)}</span>
                  <span className={cn("flex items-center gap-1 font-medium", text)}>
                    <Icon className="size-3.5" aria-hidden />
                    {label}
                  </span>
                </div>
                <p className="text-sm leading-snug">{e.description}</p>
                <ul className="mt-auto flex flex-wrap gap-1">
                  {e.objectIds.map((id) => (
                    <li key={id} className="rounded-full border border-line bg-elevated px-2 py-0.5 text-[11px] text-muted">
                      {memory.objects.find((o) => o.id === id)?.label ?? id}
                    </li>
                  ))}
                </ul>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
