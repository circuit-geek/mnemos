import { NavLink } from "react-router-dom";
import { Library, Network } from "lucide-react";
import { LogoMark } from "@/components/common/Logo";
import { Tooltip } from "@/components/ui/tooltip";
import { DEMO_VIDEO_ID } from "@/mocks/objects";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex size-9 items-center justify-center rounded-lg transition-colors",
    isActive ? "bg-accent-soft text-accent" : "text-muted hover:bg-elevated hover:text-fg",
  );

export function NavRail() {
  return (
    <nav
      aria-label="Primary"
      className="flex w-14 shrink-0 flex-col items-center gap-2 border-r border-line bg-surface py-3"
    >
      <NavLink to="/" aria-label="MNEMOS home" className="mb-3 rounded-lg">
        <LogoMark />
      </NavLink>
      <Tooltip label="Library" side="right">
        <NavLink to="/" end className={linkClass} aria-label="Library">
          <Library className="size-[18px]" />
        </NavLink>
      </Tooltip>
      <Tooltip label="Explorer" side="right">
        <NavLink
          to={`/explore/${DEMO_VIDEO_ID}`}
          className={linkClass}
          aria-label="Memory Explorer"
        >
          <Network className="size-[18px]" />
        </NavLink>
      </Tooltip>
      <div className="mt-auto">
        <ThemeToggle />
      </div>
    </nav>
  );
}
