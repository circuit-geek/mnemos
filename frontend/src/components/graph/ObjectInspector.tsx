import { useMemo } from "react";
import { History, MapPin, X } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { isRelationshipActive } from "@/services/memoryService";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatTime } from "@/lib/utils";
import type { GraphRelationship, MemoryData } from "@/types";

const PREDICATE: Record<string, string> = {
  ON: "on",
  NEXT_TO: "next to",
  INSIDE: "inside",
  NEAR: "near",
  CONTAINS: "containing",
  HOLDING: "holding",
};

function labelOf(memory: MemoryData, id: string): string {
  return memory.objects.find((o) => o.id === id)?.label ?? id;
}

function locationText(memory: MemoryData, objectId: string, t: number): string {
  const own = memory.relationships
    .filter((r) => r.sourceId === objectId && ["ON", "INSIDE", "NEXT_TO", "NEAR"].includes(r.type))
    .filter((r) => r.validFrom <= t);
  const active = own.find((r) => isRelationshipActive(r, t));
  if (active) {
    return `${PREDICATE[active.type]} ${labelOf(memory, active.targetId)}`;
  }
  const last = [...own].sort((a, b) => (b.validTo ?? Infinity) - (a.validTo ?? Infinity))[0];
  if (last && last.validTo !== null) {
    return `Last known: ${PREDICATE[last.type]} ${labelOf(memory, last.targetId)} (until ${formatTime(last.validTo)})`;
  }
  return "—";
}

function RelRow({ rel, memory, t, onJump }: { rel: GraphRelationship; memory: MemoryData; t: number; onJump: () => void }) {
  const state = isRelationshipActive(rel, t) ? "active" : t < rel.validFrom ? "upcoming" : "ended";
  return (
    <li>
      <button
        type="button"
        onClick={onJump}
        className="flex w-full items-center gap-2 rounded-lg border border-line px-2.5 py-1.5 text-left text-xs hover:border-accent/50"
      >
        <span className="min-w-0 flex-1 truncate">
          {labelOf(memory, rel.sourceId)} <span className="font-semibold text-accent">{rel.type}</span>{" "}
          {labelOf(memory, rel.targetId)}
        </span>
        <span className="shrink-0 tabular-nums text-muted">
          {formatTime(rel.validFrom)}–{rel.validTo === null ? "now" : formatTime(rel.validTo)}
        </span>
        <Badge tone={state === "active" ? "success" : state === "ended" ? "warning" : "neutral"}>{state}</Badge>
      </button>
    </li>
  );
}

export function ObjectInspector({ objectId, onClose }: { objectId: string; onClose: () => void }) {
  const { memory, timeline, graph, focusEvidence, selectObservation } = useExplorer();
  const t = timeline.currentTime;
  const object = memory.objects.find((o) => o.id === objectId);

  const history = useMemo(
    () =>
      memory.relationships
        .filter((r) => r.sourceId === objectId || r.targetId === objectId)
        .sort((a, b) => a.validFrom - b.validFrom),
    [memory.relationships, objectId],
  );
  const obsList = useMemo(
    () => memory.observations.filter((o) => o.objectId === objectId).sort((a, b) => a.timestamp - b.timestamp),
    [memory.observations, objectId],
  );
  const current = graph.snapshot.nodes.find((n) => n.id === objectId);
  // A tracked object has an observation per frame; show an even sample, always keeping first and last.
  const sampledObs = useMemo(() => {
    const MAX = 24;
    if (obsList.length <= MAX) return obsList;
    return Array.from({ length: MAX }, (_, i) => obsList[Math.round((i * (obsList.length - 1)) / (MAX - 1))]!);
  }, [obsList]);

  if (!object) return null;
  const firstObs = obsList[0];
  const lastObs = obsList[obsList.length - 1];

  return (
    <aside
      aria-label={`${object.label} inspector`}
      className="fade-in absolute inset-x-2 bottom-2 z-20 flex max-h-[46%] flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-xl"
    >
      <header className="flex items-center gap-2 border-b border-line px-3 py-2">
        <h3 className="text-sm font-semibold">{object.label}</h3>
        <Badge tone={current?.visible ? "success" : "neutral"}>
          {!current ? "not observed yet" : current.visible ? "visible now" : "not visible now"}
        </Badge>
        <code className="ml-auto truncate text-[11px] text-muted">{object.id}</code>
        <Button variant="ghost" size="icon" aria-label="Close inspector" onClick={onClose} className="size-7">
          <X className="size-4" />
        </Button>
      </header>
      <div className="overflow-y-auto px-3 py-3 text-xs">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5">
          <div>
            <dt className="text-muted">First observed</dt>
            <dd>
              {firstObs ? (
                <button
                  type="button"
                  className="font-medium tabular-nums text-accent hover:underline"
                  onClick={() => selectObservation(firstObs)}
                >
                  {formatTime(object.firstObserved)}
                </button>
              ) : (
                "—"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Last observed</dt>
            <dd>
              {lastObs ? (
                <button
                  type="button"
                  className="font-medium tabular-nums text-accent hover:underline"
                  onClick={() => selectObservation(lastObs)}
                >
                  {formatTime(object.lastObserved)}
                </button>
              ) : (
                "—"
              )}
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="flex items-center gap-1 text-muted">
              <MapPin className="size-3" aria-hidden /> Current / last known location
            </dt>
            <dd className="font-medium">{locationText(memory, objectId, t)}</dd>
          </div>
          {object.note && (
            <div className="col-span-2 text-muted">
              <dt className="sr-only">Note</dt>
              <dd>{object.note}</dd>
            </div>
          )}
        </dl>

        <h4 className="mb-1.5 mt-4 flex items-center gap-1.5 font-semibold">
          <History className="size-3.5 text-accent" aria-hidden /> Relationship history
        </h4>
        {history.length === 0 ? (
          <p className="text-muted">No relationships recorded.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {history.map((r) => {
              const ev = memory.evidence.find((e) => e.id === r.evidenceId);
              return (
                <RelRow
                  key={r.id}
                  rel={r}
                  memory={memory}
                  t={t}
                  onJump={() => (ev ? focusEvidence(ev) : timeline.seek(r.validFrom))}
                />
              );
            })}
          </ul>
        )}

        <h4 className="mb-1.5 mt-4 font-semibold">
          Evidence timestamps{" "}
          {obsList.length > sampledObs.length && (
            <span className="font-normal text-muted">
              (sample of {obsList.length} detections)
            </span>
          )}
        </h4>
        <ul className="flex flex-wrap gap-1.5">
          {sampledObs.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                onClick={() => selectObservation(o)}
                className={cn(
                  "rounded-md border px-2 py-1 tabular-nums transition-colors hover:border-accent/60",
                  Math.abs(o.timestamp - t) < 0.5 ? "border-accent bg-accent-soft text-accent" : "border-line",
                )}
              >
                {formatTime(o.timestamp)}
                <span className="ml-1.5 text-muted">{o.visibility === "visible" ? "visible" : "not visible"}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
