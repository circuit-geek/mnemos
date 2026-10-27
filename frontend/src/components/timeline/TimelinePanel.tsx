import { ChevronLeft, ChevronRight, History } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { cn, formatTime } from "@/lib/utils";
import { EVENT_META, EVENT_TYPES } from "./eventMeta";

const THUMB = 14;
/** Position inside the track, matching where the range thumb actually travels. */
const posStyle = (frac: number) => ({
  left: `calc(${THUMB / 2}px + (100% - ${THUMB}px) * ${frac})`,
});

export function TimelinePanel() {
  const { timeline, memory, graph, selection, selectEvent, stepEvent, scrubTo, video } = useExplorer();
  const { duration, currentTime } = timeline;
  const frac = (t: number) => (duration > 0 ? t / duration : 0);

  const tickStep = duration <= 60 ? 5 : duration <= 300 ? 30 : 60;
  const ticks: number[] = [];
  for (let t = 0; t <= duration; t += tickStep) ticks.push(t);

  const activeEventId = graph.focus.objectIds.size > 0 ? selection.eventId : null;

  return (
    <section aria-label="Shared timeline" className="rounded-xl border border-line bg-surface p-3 sm:p-4">
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <History className="size-4 text-accent" aria-hidden /> Timeline
        </h2>
        <div className="flex items-center gap-1">
          <Tooltip label="Previous event">
            <Button
              variant="outline"
              size="icon"
              aria-label="Previous event"
              disabled={timeline.prevEventTime === null}
              onClick={() => stepEvent(-1)}
            >
              <ChevronLeft className="size-4" />
            </Button>
          </Tooltip>
          <span className="w-[104px] text-center text-xs tabular-nums text-muted" role="timer" aria-label="Current time">
            <span className="font-semibold text-fg">{formatTime(currentTime)}</span> / {formatTime(duration)}
          </span>
          <Tooltip label="Next event">
            <Button
              variant="outline"
              size="icon"
              aria-label="Next event"
              disabled={timeline.nextEventTime === null}
              onClick={() => stepEvent(1)}
            >
              <ChevronRight className="size-4" />
            </Button>
          </Tooltip>
        </div>
        <ul className="ml-auto hidden items-center gap-3 text-[11px] text-muted md:flex" aria-label="Event types">
          {EVENT_TYPES.map((type) => (
            <li key={type} className="flex items-center gap-1.5">
              <span className={cn("size-2 rounded-full", EVENT_META[type].dot)} aria-hidden />
              {EVENT_META[type].label}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative px-1">
        {/* Event lanes, one per type */}
        <div className="flex flex-col gap-1">
          {EVENT_TYPES.map((type) => (
            <div key={type} className="relative h-5 rounded bg-elevated/60">
              {memory.events
                .filter((e) => e.type === type)
                .map((e) => {
                  const { Icon } = EVENT_META[type];
                  const active = e.id === activeEventId;
                  return (
                    <Tooltip key={e.id} label={`${formatTime(e.timestamp)} · ${e.description}`}>
                      <button
                        type="button"
                        onClick={() => selectEvent(e)}
                        aria-label={`${EVENT_META[type].label} at ${formatTime(e.timestamp)}: ${e.description}`}
                        aria-pressed={active}
                        className={cn(
                          "absolute top-1/2 grid size-[18px] -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full text-accent-fg transition-transform hover:scale-110",
                          EVENT_META[type].dot,
                          active && "scale-125 ring-2 ring-accent ring-offset-2 ring-offset-surface",
                        )}
                        style={posStyle(frac(e.timestamp))}
                      >
                        <Icon className="size-2.5" aria-hidden />
                      </button>
                    </Tooltip>
                  );
                })}
            </div>
          ))}
        </div>

        {/* Scrubber */}
        <div className="relative mt-2 h-4">
          <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-elevated" />
          <div
            className="absolute left-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-accent/70"
            style={{ width: `calc(${THUMB / 2}px + (100% - ${THUMB}px) * ${frac(currentTime)})` }}
          />
          <input
            type="range"
            className="scrubber absolute inset-0"
            aria-label="Timeline position"
            aria-valuetext={`${formatTime(currentTime)} of ${formatTime(duration)}`}
            min={0}
            max={duration}
            step={0.1}
            value={currentTime}
            disabled={duration <= 0 || video.status !== "ready"}
            onChange={(e) => scrubTo(Number(e.target.value))}
          />
        </div>

        {/* Playhead through the lanes */}
        <div
          className="pointer-events-none absolute bottom-4 top-0 w-px bg-accent/60"
          style={posStyle(frac(currentTime))}
          aria-hidden
        />

        <div className="relative mt-1 h-4 text-[10px] tabular-nums text-muted" aria-hidden>
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={posStyle(frac(t))}>
              {formatTime(t)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
