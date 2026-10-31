import { AlertCircle, Info, RotateCcw } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ReasoningMessage } from "@/types";
import { EvidenceChip } from "./EvidenceChip";

interface MessageBubbleProps {
  message: ReasoningMessage;
  onRetry?: () => void;
}

export function MessageBubble({ message, onRetry }: MessageBubbleProps) {
  const { memory, selection, selectObject } = useExplorer();

  if (message.role === "user") {
    return (
      <div className="fade-in ml-8 self-end rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-sm text-accent-fg">
        {message.content}
      </div>
    );
  }

  const objects = (message.referencedObjectIds ?? [])
    .map((id) => memory.objects.find((o) => o.id === id))
    .filter((o) => o !== undefined);

  return (
    <div
      className={cn(
        "fade-in mr-4 flex flex-col gap-3 rounded-2xl rounded-bl-md border px-3.5 py-3 text-sm",
        message.error ? "border-warning/40 bg-warning/5" : "border-line bg-elevated",
      )}
    >
      {(message.unsupported || message.error) && (
        <p className={cn("flex items-center gap-1.5 text-xs font-medium", message.error ? "text-warning" : "text-muted")}>
          {message.error ? <AlertCircle className="size-3.5" /> : <Info className="size-3.5" />}
          {message.error ? "Something went wrong" : "Not enough evidence in memory"}
        </p>
      )}
      <p className="leading-relaxed">{message.content}</p>
      {message.intent && (
        <p className="text-[11px] text-muted">
          Interpreted as <span className="font-medium text-fg">{message.intent}</span>
        </p>
      )}
      {message.error && onRetry && (
        <Button variant="outline" size="sm" className="self-start" onClick={onRetry}>
          <RotateCcw className="size-3.5" /> Retry
        </Button>
      )}
      {objects.length > 0 && (
        <div>
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted">Objects</p>
          <ul className="flex flex-wrap gap-1.5">
            {objects.map((o) => (
              <li key={o.id}>
                <button
                  type="button"
                  onClick={() => selectObject(o.id)}
                  aria-pressed={selection.objectId === o.id}
                  className={cn(
                    "rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors hover:border-accent/60",
                    selection.objectId === o.id ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface text-fg",
                  )}
                >
                  {o.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {message.evidence && message.evidence.length > 0 && (
        <div>
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted">
            Evidence · click to jump
          </p>
          <ul className="flex flex-col gap-1.5">
            {message.evidence.map((ev) => (
              <li key={ev.id}>
                <EvidenceChip evidence={ev} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
