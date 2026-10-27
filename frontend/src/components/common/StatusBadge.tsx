import { CheckCircle2, Loader2, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ProcessingStatus } from "@/types";

const CONFIG = {
  ready: { tone: "success", label: "Ready", Icon: CheckCircle2 },
  processing: { tone: "accent", label: "Processing", Icon: Loader2 },
  failed: { tone: "warning", label: "Failed", Icon: AlertTriangle },
} as const;

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const { tone, label, Icon } = CONFIG[status];
  return (
    <Badge tone={tone}>
      <Icon className={status === "processing" ? "size-3 animate-spin" : "size-3"} aria-hidden />
      {label}
    </Badge>
  );
}
