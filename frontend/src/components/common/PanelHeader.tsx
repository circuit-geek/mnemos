interface PanelHeaderProps {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function PanelHeader({ icon, title, subtitle, actions }: PanelHeaderProps) {
  return (
    <header className="flex items-center gap-2">
      <span className="text-accent">{icon}</span>
      <h2 className="text-sm font-semibold">{title}</h2>
      {subtitle && <span className="hidden text-xs text-muted sm:inline">· {subtitle}</span>}
      {actions && <div className="ml-auto flex items-center gap-1">{actions}</div>}
    </header>
  );
}
