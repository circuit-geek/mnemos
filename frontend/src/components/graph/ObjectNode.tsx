import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { Box, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ObjectCategory } from "@/types";

export interface ObjectNodeData extends Record<string, unknown> {
  label: string;
  category: ObjectCategory;
  /** Observed as visible at the current time. */
  visible: boolean;
  selected: boolean;
  /** Tied to the highlighted event / evidence. */
  focused: boolean;
}

export type ObjectFlowNode = Node<ObjectNodeData, "object">;

const hiddenHandle = { opacity: 0, pointerEvents: "none" as const, top: "50%", left: "50%" };

export function ObjectNode({ data }: NodeProps<ObjectFlowNode>) {
  const isLocation = data.category === "location";
  const Icon = isLocation ? MapPin : Box;
  return (
    <div
      className={cn(
        "flex min-w-[120px] items-center gap-2 border px-3.5 py-2.5 text-sm font-medium transition-[box-shadow,border-color,opacity] duration-150",
        isLocation
          ? "rounded-full border-dashed border-line bg-elevated text-muted"
          : "rounded-xl border-line bg-surface text-fg",
        !data.visible && "opacity-55",
        data.focused && "border-warning ring-2 ring-warning/40",
        data.selected && "border-accent bg-accent-soft ring-2 ring-accent/40",
      )}
    >
      <Handle type="target" position={Position.Top} style={hiddenHandle} isConnectable={false} />
      <Icon className={cn("size-4 shrink-0", data.selected ? "text-accent" : "text-muted")} aria-hidden />
      <span className="flex flex-col leading-tight">
        <span>{data.label}</span>
        {!data.visible && <span className="text-[10px] font-normal text-muted">not visible</span>}
      </span>
      <Handle type="source" position={Position.Bottom} style={hiddenHandle} isConnectable={false} />
    </div>
  );
}
