import * as TooltipPrimitive from "@radix-ui/react-tooltip";

export const TooltipProvider = TooltipPrimitive.Provider;

interface TooltipProps {
  label: string;
  children: React.ReactElement;
  side?: "top" | "bottom" | "left" | "right";
}

export function Tooltip({ label, children, side = "top" }: TooltipProps) {
  return (
    <TooltipPrimitive.Root delayDuration={300}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className="z-50 rounded-md border border-line bg-elevated px-2 py-1 text-xs text-fg shadow-lg"
        >
          {label}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
