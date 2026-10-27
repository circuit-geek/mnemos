import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useTimeline, type TimelineState } from "@/hooks/useTimeline";
import { useMemoryGraph, type MemoryGraphView } from "@/hooks/useMemoryGraph";
import type {
  EvidenceReference,
  MemoryData,
  MemoryEvent,
  ObjectObservation,
  Selection,
  VideoRecord,
} from "@/types";

interface ExplorerContextValue {
  video: VideoRecord;
  memory: MemoryData;
  hasMemory: boolean;
  timeline: TimelineState;
  graph: MemoryGraphView;
  selection: Selection;
  selectObject: (objectId: string | null) => void;
  selectEvent: (event: MemoryEvent) => void;
  focusEvidence: (evidence: EvidenceReference) => void;
  selectObservation: (obs: ObjectObservation) => void;
  /** Manual scrubbing: keeps object selection, lets event highlights lapse. */
  scrubTo: (t: number) => void;
  stepEvent: (direction: -1 | 1) => void;
}

const ExplorerContext = createContext<ExplorerContextValue | null>(null);

const EMPTY_SELECTION: Selection = { objectId: null, eventId: null, evidenceId: null };

export function ExplorerProvider({
  video,
  memory,
  children,
}: {
  video: VideoRecord;
  memory: MemoryData;
  children: React.ReactNode;
}) {
  const timeline = useTimeline(video.duration, memory.events);
  const [selection, setSelection] = useState<Selection>(EMPTY_SELECTION);
  const graph = useMemoryGraph(memory, timeline.currentTime, selection);
  const { seek, pause } = timeline;

  const selectObject = useCallback(
    (objectId: string | null) =>
      setSelection(objectId === null ? EMPTY_SELECTION : { objectId, eventId: null, evidenceId: null }),
    [],
  );

  const selectEvent = useCallback(
    (event: MemoryEvent) => {
      pause();
      seek(event.timestamp);
      setSelection({
        objectId: event.objectIds[0] ?? null,
        eventId: event.id,
        evidenceId: event.evidenceId,
      });
    },
    [pause, seek],
  );

  const focusEvidence = useCallback(
    (ev: EvidenceReference) => {
      pause();
      seek(ev.timestamp);
      setSelection({
        objectId: ev.objectIds[0] ?? null,
        eventId: ev.eventId ?? null,
        evidenceId: ev.id,
      });
    },
    [pause, seek],
  );

  const selectObservation = useCallback(
    (obs: ObjectObservation) => {
      pause();
      seek(obs.timestamp);
      setSelection({ objectId: obs.objectId, eventId: null, evidenceId: obs.evidenceId });
    },
    [pause, seek],
  );

  const scrubTo = useCallback((t: number) => seek(t), [seek]);

  const stepEvent = useCallback(
    (direction: -1 | 1) => {
      const target = direction < 0 ? timeline.prevEventTime : timeline.nextEventTime;
      if (target === null) return;
      const event = memory.events.find((e) => e.timestamp === target);
      if (event) selectEvent(event);
      else seek(target);
    },
    [timeline.prevEventTime, timeline.nextEventTime, memory.events, selectEvent, seek],
  );

  const value = useMemo<ExplorerContextValue>(
    () => ({
      video,
      memory,
      hasMemory: memory.objects.length > 0,
      timeline,
      graph,
      selection,
      selectObject,
      selectEvent,
      focusEvidence,
      selectObservation,
      scrubTo,
      stepEvent,
    }),
    [video, memory, timeline, graph, selection, selectObject, selectEvent, focusEvidence, selectObservation, scrubTo, stepEvent],
  );

  return <ExplorerContext.Provider value={value}>{children}</ExplorerContext.Provider>;
}

export function useExplorer(): ExplorerContextValue {
  const ctx = useContext(ExplorerContext);
  if (!ctx) throw new Error("useExplorer must be used inside ExplorerProvider");
  return ctx;
}
