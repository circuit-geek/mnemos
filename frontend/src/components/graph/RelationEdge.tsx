import {
  BaseEdge,
  EdgeLabelRenderer,
  getStraightPath,
  useInternalNode,
  type Edge,
  type EdgeProps,
  type InternalNode,
} from "@xyflow/react";
import { cn, formatTime } from "@/lib/utils";
import type { RelationshipType } from "@/types";

export type EdgeState = "active" | "highlight" | "ended";

export interface RelationEdgeData extends Record<string, unknown> {
  type: RelationshipType;
  state: EdgeState;
  /** Set for ended relationships, shown in the label. */
  endedAt?: number;
}

export type RelationFlowEdge = Edge<RelationEdgeData, "relation">;

/** Point where the line from this node's centre to `other`'s centre leaves its rectangle. */
function borderPoint(node: InternalNode, other: InternalNode) {
  const w = (node.measured.width ?? 0) / 2;
  const h = (node.measured.height ?? 0) / 2;
  const c = { x: node.internals.positionAbsolute.x + w, y: node.internals.positionAbsolute.y + h };
  const o = {
    x: other.internals.positionAbsolute.x + (other.measured.width ?? 0) / 2,
    y: other.internals.positionAbsolute.y + (other.measured.height ?? 0) / 2,
  };
  const dx = o.x - c.x;
  const dy = o.y - c.y;
  if (dx === 0 && dy === 0) return c;
  const scale = 1 / Math.max(Math.abs(dx) / (w || 1), Math.abs(dy) / (h || 1));
  return { x: c.x + dx * scale, y: c.y + dy * scale };
}

export function RelationEdge({ id, source, target, data, markerEnd }: EdgeProps<RelationFlowEdge>) {
  const s = useInternalNode(source);
  const t = useInternalNode(target);
  if (!s || !t || !data) return null;

  const a = borderPoint(s, t);
  const b = borderPoint(t, s);
  const [path, labelX, labelY] = getStraightPath({
    sourceX: a.x,
    sourceY: a.y,
    targetX: b.x,
    targetY: b.y,
  });
  const { state } = data;
  const label =
    state === "ended" && data.endedAt !== undefined
      ? `${data.type} · ended ${formatTime(data.endedAt)}`
      : data.type;

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          stroke: state === "highlight" ? "var(--accent)" : state === "ended" ? "var(--warning)" : "var(--muted)",
          strokeWidth: state === "highlight" ? 2.5 : 1.5,
          strokeDasharray: state === "ended" ? "6 5" : undefined,
          transition: "stroke 150ms, stroke-width 150ms",
        }}
      />
      <EdgeLabelRenderer>
        <div
          className={cn(
            "nodrag nopan pointer-events-none absolute rounded-md border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide",
            state === "highlight" && "border-accent bg-accent-soft text-accent",
            state === "ended" && "border-warning/50 bg-surface text-warning",
            state === "active" && "border-line bg-surface text-muted",
          )}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
