import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  MarkerType,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type NodeTypes,
  type EdgeTypes,
} from "@xyflow/react";
import { Maximize2, Network, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { EmptyState } from "@/components/common/EmptyState";
import { PanelHeader } from "@/components/common/PanelHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTime } from "@/lib/utils";
import { ObjectNode, type ObjectFlowNode } from "./ObjectNode";
import { RelationEdge, type RelationFlowEdge } from "./RelationEdge";
import { GraphLegend } from "./GraphLegend";
import { ObjectInspector } from "./ObjectInspector";

const nodeTypes: NodeTypes = { object: ObjectNode };
const edgeTypes: EdgeTypes = { relation: RelationEdge };

const NODE_W = 150;
const NODE_H = 52;
const FIT_PADDING = 0.18;

/**
 * Fixed positions on an ellipse, by object order, so nodes never move while seeking and
 * any number of objects stays readable.
 */
function layoutPosition(index: number, total: number) {
  if (total <= 1) return { x: 0, y: 0 };
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / total;
  const radius = Math.max(150, total * 48);
  return { x: Math.cos(angle) * radius * 1.35, y: Math.sin(angle) * radius * 0.85 };
}

function GraphCanvas() {
  const { memory, graph, selection, selectObject } = useExplorer();
  const rf = useReactFlow();
  const wrapRef = useRef<HTMLDivElement>(null);
  // The inspector covers the lower part of the canvas, so frame the graph higher while it is open.
  const inspectorOpen = selection.objectId !== null;

  const nodes = useMemo<ObjectFlowNode[]>(
    () =>
      graph.snapshot.nodes.map((n) => ({
        id: n.id,
        type: "object",
        position: layoutPosition(memory.objects.findIndex((o) => o.id === n.id), memory.objects.length),
        draggable: false,
        ariaLabel: `${n.label}${n.visible ? "" : " (not visible)"}`,
        data: {
          label: n.label,
          category: n.category,
          visible: n.visible,
          selected: selection.objectId === n.id,
          focused: graph.focus.objectIds.has(n.id),
        },
      })),
    [graph.snapshot.nodes, graph.focus.objectIds, selection.objectId, memory.objects],
  );

  const edges = useMemo<RelationFlowEdge[]>(() => {
    const present = new Set(graph.snapshot.nodes.map((n) => n.id));
    const build = (
      r: (typeof memory.relationships)[number],
      state: "active" | "highlight" | "ended",
    ): RelationFlowEdge => {
      const color = state === "highlight" ? "var(--accent)" : state === "ended" ? "var(--warning)" : "var(--muted)";
      return {
        id: r.id,
        source: r.sourceId,
        target: r.targetId,
        type: "relation",
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color },
        data: {
          type: r.type,
          state,
          endedAt: state === "ended" && r.validTo !== null ? r.validTo : undefined,
        },
      };
    };
    const active = graph.snapshot.relationships.map((r) => {
      const hot =
        graph.focus.relationshipIds.has(r.id) ||
        r.sourceId === selection.objectId ||
        r.targetId === selection.objectId;
      return build(r, hot ? "highlight" : "active");
    });
    const ended = graph.endedRelationships.map((r) => build(r, "ended"));
    return [...active, ...ended].filter((e) => present.has(e.source) && present.has(e.target));
  }, [graph, selection.objectId, memory]);

  const fitAll = useCallback(
    (duration = 0) => {
      const ids = memory.objects.map((_, i) => layoutPosition(i, memory.objects.length));
      if (ids.length === 0) return;
      const minX = Math.min(...ids.map((p) => p.x));
      const minY = Math.min(...ids.map((p) => p.y));
      const maxX = Math.max(...ids.map((p) => p.x)) + NODE_W;
      const maxY = Math.max(...ids.map((p) => p.y)) + NODE_H;
      void rf.fitBounds(
        { x: minX, y: minY, width: maxX - minX, height: (maxY - minY) * (inspectorOpen ? 1.8 : 1) },
        { padding: FIT_PADDING, duration },
      );
    },
    [rf, memory.objects, inspectorOpen],
  );

  // Re-frame when the inspector opens or closes (not when switching between objects).
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    fitAll(200);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inspectorOpen]);

  // Keep the graph framed when the panel resizes (e.g. the sidebar toggles).
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    let timer: number | undefined;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fitAll(150), 180);
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      window.clearTimeout(timer);
    };
  }, [fitAll]);

  return (
    <div ref={wrapRef} className="size-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={() => fitAll(0)}
        onNodeClick={(_, node) => selectObject(node.id)}
        onPaneClick={() => selectObject(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        aria-label="Temporal knowledge graph"
      >
        <Panel position="top-left" className="flex flex-col items-start gap-2">
          <span className="rounded-lg border border-line bg-surface/95 px-2.5 py-1 text-xs font-medium tabular-nums text-muted backdrop-blur">
            Graph at <span className="text-fg">{formatTime(graph.snapshot.timestamp)}</span>
          </span>
          <GraphLegend />
        </Panel>
        <Panel position="top-right" className="flex flex-col gap-1 rounded-lg border border-line bg-surface/95 p-1 backdrop-blur">
          <Tooltip label="Zoom in" side="left">
            <Button variant="ghost" size="icon" aria-label="Zoom in" onClick={() => void rf.zoomIn({ duration: 150 })}>
              <ZoomIn className="size-4" />
            </Button>
          </Tooltip>
          <Tooltip label="Zoom out" side="left">
            <Button variant="ghost" size="icon" aria-label="Zoom out" onClick={() => void rf.zoomOut({ duration: 150 })}>
              <ZoomOut className="size-4" />
            </Button>
          </Tooltip>
          <Tooltip label="Fit visible nodes" side="left">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Fit to screen"
              onClick={() => void rf.fitView({ padding: FIT_PADDING, duration: 200 })}
            >
              <Maximize2 className="size-4" />
            </Button>
          </Tooltip>
          <Tooltip label="Reset view and selection" side="left">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Reset view"
              onClick={() => {
                selectObject(null);
                fitAll(200);
              }}
            >
              <RotateCcw className="size-4" />
            </Button>
          </Tooltip>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export function KnowledgeGraph({ loading = false }: { loading?: boolean }) {
  const { hasMemory, selection, selectObject } = useExplorer();
  return (
    <section aria-label="Temporal knowledge graph" className="flex min-h-0 flex-col gap-3">
      <PanelHeader
        icon={<Network className="size-4" />}
        title="Temporal Knowledge Graph"
        subtitle="Relationships valid at the current time"
      />
      <div className="relative h-[380px] overflow-hidden rounded-xl border border-line bg-surface lg:h-auto lg:min-h-[320px] lg:flex-1">
        {loading ? (
          <Skeleton className="size-full rounded-none" />
        ) : hasMemory ? (
          <ReactFlowProvider>
            <GraphCanvas />
          </ReactFlowProvider>
        ) : (
          <EmptyState
            icon={<Network className="size-5" />}
            title="No memory graph"
            description="This prototype has no backend to build a knowledge graph from uploaded videos. Open the Office Desk Demo to explore one."
          />
        )}
        {selection.objectId && hasMemory && (
          <ObjectInspector objectId={selection.objectId} onClose={() => selectObject(null)} />
        )}
      </div>
    </section>
  );
}
