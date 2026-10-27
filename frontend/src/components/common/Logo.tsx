import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-8", className)} aria-hidden>
      <rect width="32" height="32" rx="8" className="fill-accent-soft" />
      <path d="M10 22 22 10M10 22h12" className="stroke-accent" strokeWidth="1.5" fill="none" />
      <circle cx="10" cy="22" r="3" className="fill-accent" />
      <circle cx="22" cy="10" r="3" className="fill-accent" />
      <circle cx="22" cy="22" r="2" className="fill-muted" />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("text-sm font-semibold tracking-[0.18em] text-fg", className)}>
      MNEMOS
    </span>
  );
}
