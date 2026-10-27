import { useCallback, useMemo, useState } from "react";
import { clamp } from "@/lib/utils";
import type { MemoryEvent } from "@/types";

export const PLAYBACK_RATES = [0.5, 1, 1.5, 2] as const;

const EPS = 0.05;

/**
 * Single source of truth for playback time. The video player, graph, event
 * list and chat evidence all read from and write to this state.
 */
export function useTimeline(duration: number, events: MemoryEvent[]) {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [rate, setRate] = useState<number>(1);

  const seek = useCallback(
    (t: number) => setCurrentTime(clamp(t, 0, duration)),
    [duration],
  );

  /** Called by the player as media time advances. Stops at the end. */
  const reportTime = useCallback(
    (t: number) => {
      if (t >= duration) {
        setCurrentTime(duration);
        setIsPlaying(false);
      } else {
        setCurrentTime(Math.max(0, t));
      }
    },
    [duration],
  );

  const play = useCallback(() => {
    setCurrentTime((t) => (t >= duration ? 0 : t));
    setIsPlaying(true);
  }, [duration]);
  const pause = useCallback(() => setIsPlaying(false), []);
  const toggle = useCallback(() => {
    setIsPlaying((p) => !p);
    setCurrentTime((t) => (t >= duration ? 0 : t));
  }, [duration]);

  const eventTimes = useMemo(
    () => [...new Set(events.map((e) => e.timestamp))].sort((a, b) => a - b),
    [events],
  );
  const prevEventTime = useMemo(
    () => [...eventTimes].reverse().find((t) => t < currentTime - EPS) ?? null,
    [eventTimes, currentTime],
  );
  const nextEventTime = useMemo(
    () => eventTimes.find((t) => t > currentTime + EPS) ?? null,
    [eventTimes, currentTime],
  );

  return {
    duration,
    currentTime,
    isPlaying,
    rate,
    setRate,
    seek,
    reportTime,
    play,
    pause,
    toggle,
    eventTimes,
    prevEventTime,
    nextEventTime,
  };
}

export type TimelineState = ReturnType<typeof useTimeline>;
