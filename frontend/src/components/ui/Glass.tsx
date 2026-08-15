// Glass panel primitive — V3 recipe (docs/frontend_overhaul.md V3 §4):
// visible alpha-gradient fill over the WebGL aurora, gradient border, optional
// neon edge, hover lift, a cursor-tracking spotlight on every panel, and a
// `beam` variant (animated conic border sweep) for hero surfaces. Styles live
// in tokens.css; `hue` feeds --panel-hue so each panel glows its own color
// (the multi-hue rule: panels stop inheriting one global accent).
import type { HTMLAttributes, MouseEvent } from "react";

interface GlassProps extends HTMLAttributes<HTMLDivElement> {
  /** brighter fill for hero surfaces */
  strong?: boolean;
  /** neon edge stroke + glow — reserve for interactive glass */
  neon?: boolean;
  /** lifts on hover (adds the §3.3 card affordance) */
  lift?: boolean;
  /** animated conic border sweep — reserve for the hero panel of a view */
  beam?: boolean;
  /** disable the cursor spotlight (dense list panels) */
  still?: boolean;
  /** CSS color for this panel's glow; defaults to the dominant accent */
  hue?: string;
}

// One shared handler writes CSS vars directly — no React re-render per move.
function trackSpot(e: MouseEvent<HTMLDivElement>) {
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  el.style.setProperty("--mx", `${(((e.clientX - r.left) / r.width) * 100).toFixed(2)}%`);
  el.style.setProperty("--my", `${(((e.clientY - r.top) / r.height) * 100).toFixed(2)}%`);
}

export function Glass({
  strong,
  neon,
  lift,
  beam,
  still,
  hue,
  className = "",
  style,
  children,
  onMouseMove,
  ...rest
}: GlassProps) {
  const cls = [
    "glass",
    strong ? "glass-strong" : "",
    neon ? "glass-neon" : "",
    lift ? "hover-lift" : "",
    beam ? "glass-beam" : "",
    still ? "" : "glass-spot",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const styles = hue
    ? ({ ...style, "--panel-hue": hue } as React.CSSProperties)
    : style;
  const handleMove = still
    ? onMouseMove
    : (e: MouseEvent<HTMLDivElement>) => {
        trackSpot(e);
        onMouseMove?.(e);
      };
  return (
    <div className={cls} style={styles} onMouseMove={handleMove} {...rest}>
      {children}
    </div>
  );
}
