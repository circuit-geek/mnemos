import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <Tooltip label={`Switch to ${next} theme`} side="right">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        aria-label={`Switch to ${next} theme`}
      >
        {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
      </Button>
    </Tooltip>
  );
}
