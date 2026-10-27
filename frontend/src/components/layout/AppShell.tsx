import { Outlet } from "react-router-dom";
import { NavRail } from "./NavRail";

export function AppShell() {
  return (
    <div className="flex h-full min-h-0">
      <NavRail />
      <main className="min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
