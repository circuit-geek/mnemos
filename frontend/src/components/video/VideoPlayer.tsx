import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Maximize, Minimize, Pause, Play, ScanSearch, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tooltip } from "@/components/ui/tooltip";
import { EmptyState } from "@/components/common/EmptyState";
import { PLAYBACK_RATES } from "@/hooks/useTimeline";
import { getContentRect, type Rect } from "@/lib/geometry";
import { cn, formatTime } from "@/lib/utils";

interface VideoPlayerProps {
  /** Object URL / media URL. Omit to render `fallback` on a virtual clock. */
  src?: string;
  /** Rendered in place of a video (e.g. a labeled scene illustration). */
  fallback?: React.ReactNode;
  /** Intrinsic size of `fallback`, used for letterbox maths. */
  fallbackAspect?: { width: number; height: number };
  /** Small label pinned to the picture, e.g. "Sample scene illustration". */
  mediaLabel?: string;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  rate: number;
  onTimeUpdate: (t: number) => void;
  onTogglePlay: () => void;
  onSeek: (t: number) => void;
  onRateChange: (rate: number) => void;
  overlayEnabled: boolean;
  onOverlayEnabledChange: (v: boolean) => void;
  /** False when no detection data exists for this recording. */
  overlayAvailable: boolean;
  /** Renders on top of the media, in container pixels aligned to the picture. */
  renderOverlay?: (content: Rect) => React.ReactNode;
  className?: string;
}

const REPORT_STEP_S = 0.05;

export function VideoPlayer({
  src,
  fallback,
  fallbackAspect,
  mediaLabel,
  duration,
  currentTime,
  isPlaying,
  rate,
  onTimeUpdate,
  onTogglePlay,
  onSeek,
  onRateChange,
  overlayEnabled,
  onOverlayEnabledChange,
  overlayAvailable,
  renderOverlay,
  className,
}: VideoPlayerProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const clockRef = useRef(currentTime);
  const lastReportedRef = useRef(currentTime);
  const latest = useRef({ currentTime, onTimeUpdate });
  latest.current = { currentTime, onTimeUpdate };

  const [stageSize, setStageSize] = useState({ w: 0, h: 0 });
  const [mediaSize, setMediaSize] = useState<{ w: number; h: number } | null>(null);
  const [mediaState, setMediaState] = useState<"loading" | "ready" | "error">(
    src ? "loading" : "ready",
  );
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setStageSize({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  // Reset load state when the source changes.
  useEffect(() => {
    setMediaState(src ? "loading" : "ready");
    setMediaSize(null);
  }, [src]);

  const intrinsic = src
    ? mediaSize
    : fallbackAspect
      ? { w: fallbackAspect.width, h: fallbackAspect.height }
      : null;
  const content = useMemo(
    () =>
      intrinsic
        ? getContentRect(stageSize.w, stageSize.h, intrinsic.w, intrinsic.h)
        : { left: 0, top: 0, width: stageSize.w, height: stageSize.h },
    [intrinsic, stageSize.w, stageSize.h],
  );

  /* ---- real media sync ---- */
  useEffect(() => {
    const v = videoRef.current;
    if (v) v.playbackRate = rate;
  }, [rate, src]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v || mediaState !== "ready") return;
    if (isPlaying) {
      void v.play().catch(() => onTogglePlay());
    } else {
      v.pause();
    }
    // onTogglePlay is only used to recover from a rejected play().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, mediaState]);

  useEffect(() => {
    const v = videoRef.current;
    if (v && mediaState === "ready" && Math.abs(v.currentTime - currentTime) > 0.3) {
      v.currentTime = currentTime;
    }
  }, [currentTime, mediaState]);

  /* ---- playback clock: real media time, or a virtual clock for the illustration ---- */
  const report = useCallback((t: number) => {
    if (Math.abs(t - lastReportedRef.current) >= REPORT_STEP_S || t >= duration) {
      lastReportedRef.current = t;
      latest.current.onTimeUpdate(t);
    }
  }, [duration]);

  useEffect(() => {
    if (!isPlaying) return;
    clockRef.current = latest.current.currentTime;
    lastReportedRef.current = clockRef.current;
    let prev = performance.now();
    const tick = () => {
      const now = performance.now();
      const dt = (now - prev) / 1000;
      prev = now;
      const v = videoRef.current;
      if (src) {
        if (v && mediaState === "ready") report(v.currentTime);
      } else {
        // An external seek moves currentTime far from our clock; follow it.
        if (Math.abs(latest.current.currentTime - clockRef.current) > 0.2) {
          clockRef.current = latest.current.currentTime;
        }
        clockRef.current += dt * rate;
        report(Math.min(clockRef.current, duration));
      }
    };
    const timer = window.setInterval(tick, 50);
    return () => window.clearInterval(timer);
  }, [isPlaying, src, rate, duration, mediaState, report]);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void rootRef.current?.requestFullscreen?.();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.target !== rootRef.current) return;
    if (e.key === " " || e.key === "k") {
      e.preventDefault();
      onTogglePlay();
    } else if (e.key === "ArrowRight") onSeek(currentTime + 1);
    else if (e.key === "ArrowLeft") onSeek(currentTime - 1);
  };

  const unavailable = mediaState === "error";

  return (
    <div
      ref={rootRef}
      tabIndex={0}
      onKeyDown={onKeyDown}
      aria-label="Video player. Space plays or pauses, arrow keys seek one second."
      className={cn("flex min-h-0 flex-col overflow-hidden rounded-xl border border-line bg-surface", className)}
    >
      <div ref={stageRef} className="relative min-h-0 flex-1 bg-black/90 dark:bg-black/40">
        {src && !unavailable && (
          <video
            ref={videoRef}
            src={src}
            playsInline
            preload="auto"
            className="absolute inset-0 size-full object-contain"
            onLoadedMetadata={(e) => {
              const v = e.currentTarget;
              setMediaSize({ w: v.videoWidth, h: v.videoHeight });
              setMediaState("ready");
            }}
            onError={() => setMediaState("error")}
            onEnded={() => onTimeUpdate(duration)}
          />
        )}
        {!src && fallback && (
          <div
            className="absolute overflow-hidden"
            style={{
              left: content.left,
              top: content.top,
              width: content.width,
              height: content.height,
            }}
          >
            {fallback}
          </div>
        )}
        {mediaLabel && !unavailable && (
          <span
            className="absolute z-10 rounded-md border border-line bg-surface/90 px-2 py-0.5 text-[11px] font-medium text-muted backdrop-blur"
            style={{ left: content.left + 8, top: content.top + 8 }}
          >
            {mediaLabel}
          </span>
        )}
        {overlayEnabled && overlayAvailable && !unavailable && renderOverlay && (
          <div className="pointer-events-none absolute inset-0 z-10">{renderOverlay(content)}</div>
        )}
        {mediaState === "loading" && (
          <div className="absolute inset-0 grid place-items-center text-xs text-muted">
            <div className="animate-pulse">Loading video…</div>
          </div>
        )}
        {unavailable && (
          <EmptyState
            className="absolute inset-0 bg-surface"
            icon={<VideoOff className="size-5" />}
            title="Video unavailable"
            description="This file couldn't be played in your browser. Try an MP4 (H.264) or WebM file."
          />
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-line px-3 py-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onTogglePlay}
          disabled={unavailable}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause className="size-4" /> : <Play className="size-4" />}
        </Button>
        <span className="w-[88px] shrink-0 text-xs tabular-nums text-muted" aria-live="off">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
        <input
          type="range"
          aria-label="Seek video"
          min={0}
          max={duration}
          step={0.1}
          value={currentTime}
          disabled={unavailable || duration <= 0}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="h-1.5 min-w-24 flex-1 cursor-pointer accent-accent"
        />
        <label className="flex items-center gap-1 text-xs text-muted">
          <span className="sr-only">Playback speed</span>
          <select
            value={rate}
            onChange={(e) => onRateChange(Number(e.target.value))}
            className="h-8 rounded-md border border-line bg-elevated px-1.5 text-xs text-fg"
          >
            {PLAYBACK_RATES.map((r) => (
              <option key={r} value={r}>
                {r}×
              </option>
            ))}
          </select>
        </label>
        <Tooltip label={overlayAvailable ? "Show object detections" : "No detections for this recording"}>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
            <ScanSearch className="size-4" aria-hidden />
            <span className="hidden sm:inline">Detections</span>
            <Switch
              checked={overlayEnabled && overlayAvailable}
              disabled={!overlayAvailable}
              onCheckedChange={onOverlayEnabledChange}
              aria-label="Toggle object detection overlay"
            />
          </label>
        </Tooltip>
        <Tooltip label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          >
            {isFullscreen ? <Minimize className="size-4" /> : <Maximize className="size-4" />}
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}
