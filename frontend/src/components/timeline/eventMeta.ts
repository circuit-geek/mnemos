import { Eye, EyeOff, GitCompareArrows, Move, type LucideIcon } from "lucide-react";
import type { MemoryEventType } from "@/types";

export const EVENT_META: Record<
  MemoryEventType,
  { label: string; Icon: LucideIcon; dot: string; text: string }
> = {
  object_appeared: { label: "Object appeared", Icon: Eye, dot: "bg-success", text: "text-success" },
  object_disappeared: { label: "Object disappeared", Icon: EyeOff, dot: "bg-warning", text: "text-warning" },
  object_moved: { label: "Object moved", Icon: Move, dot: "bg-accent", text: "text-accent" },
  relationship_changed: {
    label: "Relationship changed",
    Icon: GitCompareArrows,
    dot: "bg-fg",
    text: "text-fg",
  },
};

export const EVENT_TYPES = Object.keys(EVENT_META) as MemoryEventType[];
