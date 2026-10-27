import { useMemo, useState } from "react";
import { Eye } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { VideoPlayer } from "./VideoPlayer";
import { SceneIllustration, SCENE_ASPECT } from "./SceneIllustration";
import { DetectionOverlay, type Detection } from "./DetectionOverlay";
import { ObjectChips } from "./ObjectChips";
import { EmptyState } from "@/components/common/EmptyState";
import { PanelHeader } from "@/components/common/PanelHeader";

export function VisualPerceptionPanel() {
  const { video, memory, hasMemory, timeline, graph, selection, selectObject, scrubTo } = useExplorer();
  const [overlayEnabled, setOverlayEnabled] = useState(true);

  const { visibleIds, observedIds, detections } = useMemo(() => {
    const visible = new Set<string>();
    const observed = new Set<string>();
    const dets: Detection[] = [];
    for (const o of graph.snapshot.observations) {
      observed.add(o.objectId);
      if (o.visibility !== "visible") continue;
      visible.add(o.objectId);
      const label = memory.objects.find((x) => x.id === o.objectId)?.label;
      if (o.boundingBox && label) dets.push({ objectId: o.objectId, label, box: o.boundingBox });
    }
    return { visibleIds: visible, observedIds: observed, detections: dets };
  }, [graph.snapshot, memory.objects]);

  const isIllustration = video.mediaKind === "scene-illustration";

  return (
    <section aria-label="Visual perception" className="flex min-h-0 flex-col gap-3">
      <PanelHeader icon={<Eye className="size-4" />} title="Visual Perception" subtitle="Objects detected in the video" />
      <VideoPlayer
        className="aspect-video min-h-[220px] lg:aspect-auto lg:flex-1"
        src={isIllustration ? undefined : video.videoUrl}
        fallback={isIllustration ? <SceneIllustration visibleObjectIds={visibleIds} /> : undefined}
        fallbackAspect={SCENE_ASPECT}
        mediaLabel={isIllustration ? "Sample scene illustration · not a recording" : undefined}
        duration={video.duration}
        currentTime={timeline.currentTime}
        isPlaying={timeline.isPlaying}
        rate={timeline.rate}
        onTimeUpdate={timeline.reportTime}
        onTogglePlay={timeline.toggle}
        onSeek={scrubTo}
        onRateChange={timeline.setRate}
        overlayEnabled={overlayEnabled}
        onOverlayEnabledChange={setOverlayEnabled}
        overlayAvailable={hasMemory}
        renderOverlay={(content) => (
          <DetectionOverlay
            content={content}
            detections={detections}
            selectedObjectId={selection.objectId}
            focusObjectIds={graph.focus.objectIds}
            onSelect={selectObject}
          />
        )}
      />
      <div className="min-h-9">
        {hasMemory ? (
          <ObjectChips
            objects={memory.objects}
            visibleIds={visibleIds}
            observedIds={observedIds}
            selectedId={selection.objectId}
            onSelect={selectObject}
          />
        ) : (
          <EmptyState
            className="!flex-row !justify-start !gap-3 !p-0 text-left"
            icon={<Eye className="size-4" />}
            title="No detections"
            description="Uploads are not analyzed in this prototype, so there are no detected objects."
          />
        )}
      </div>
    </section>
  );
}
