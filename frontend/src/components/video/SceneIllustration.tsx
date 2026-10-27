import { cn } from "@/lib/utils";

export const SCENE_ASPECT = { width: 1600, height: 900 } as const;

interface SceneIllustrationProps {
  /** Object ids currently visible; omit to draw every object. */
  visibleObjectIds?: ReadonlySet<string>;
  className?: string;
}

/**
 * Stylised stand-in for the sample recording. Shapes are laid out to match the
 * normalised boxes in `mocks/objects.ts` (1600×900 space).
 */
export function SceneIllustration({ visibleObjectIds, className }: SceneIllustrationProps) {
  const show = (id: string) => !visibleObjectIds || visibleObjectIds.has(id);
  return (
    <svg
      viewBox={`0 0 ${SCENE_ASPECT.width} ${SCENE_ASPECT.height}`}
      className={cn("block size-full", className)}
      role="img"
      aria-label="Illustration of an office desk with a laptop, a chair and, depending on the time, a coffee mug or a notebook"
    >
      <rect width="1600" height="900" className="fill-[var(--scene-wall)]" />
      <rect y="830" width="1600" height="70" className="fill-line" opacity="0.6" />
      <rect x="1000" y="70" width="460" height="170" rx="10" className="fill-surface stroke-line" strokeWidth="3" />
      <path d="M1230 70v170M1000 155h460" className="stroke-line" strokeWidth="3" />

      {/* Desk */}
      <g>
        <rect x="130" y="580" width="30" height="284" className="fill-line" />
        <rect x="1120" y="580" width="30" height="284" className="fill-line" />
        <rect x="96" y="540" width="1088" height="42" rx="8" className="fill-elevated stroke-line" strokeWidth="3" />
      </g>

      {/* Laptop */}
      {show("obj-laptop") && (
        <g>
          <rect x="344" y="276" width="336" height="236" rx="12" className="fill-[#0f1623] stroke-line" strokeWidth="4" />
          <rect x="364" y="296" width="296" height="196" rx="4" className="fill-accent" opacity="0.16" />
          <path d="M386 330h150M386 360h210M386 390h120M386 420h180" className="stroke-accent" strokeWidth="6" strokeLinecap="round" opacity="0.6" />
          <path d="M304 530h416l-18 19H322z" className="fill-elevated stroke-line" strokeWidth="3" strokeLinejoin="round" />
          <rect x="344" y="512" width="336" height="18" className="fill-elevated stroke-line" strokeWidth="3" />
        </g>
      )}

      {/* Coffee mug */}
      {show("obj-mug") && (
        <g>
          <rect x="850" y="424" width="94" height="125" rx="14" fill="#c9a27e" />
          <path d="M944 452h14a22 22 0 0 1 0 54h-14" fill="none" stroke="#c9a27e" strokeWidth="14" />
          <rect x="850" y="424" width="94" height="22" rx="10" fill="#7a5a43" />
        </g>
      )}

      {/* Notebook */}
      {show("obj-notebook") && (
        <g>
          <path d="M734 584l20-58h238l-12 58z" className="fill-accent" opacity="0.85" />
          <path d="M754 526l-6 24h232" className="stroke-accent-fg" strokeWidth="3" fill="none" opacity="0.5" />
        </g>
      )}

      {/* Chair */}
      <g>
        <rect x="1288" y="326" width="190" height="290" rx="26" className="fill-elevated stroke-line" strokeWidth="4" />
        <rect x="1250" y="620" width="268" height="52" rx="18" className="fill-elevated stroke-line" strokeWidth="4" />
        <path d="M1384 672v150M1300 672l-40 160M1470 672l40 160" className="stroke-line" strokeWidth="14" strokeLinecap="round" />
      </g>
    </svg>
  );
}
