import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex h-full flex-col items-center justify-center gap-2 p-6 text-center", className)}>
      <div className="flex size-10 items-center justify-center rounded-full border border-line bg-elevated text-muted">
        {icon}
      </div>
      <p className="text-sm font-medium text-fg">{title}</p>
      {description && <p className="max-w-xs text-xs leading-relaxed text-muted">{description}</p>}
      {action}
    </div>
  );
}
