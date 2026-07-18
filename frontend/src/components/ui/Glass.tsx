// Glass panel primitive — V2 recipe (docs/frontend_overhaul.md §3.2):
// visible alpha-gradient fill over the bright aurora, gradient border,
// optional neon edge (interactive glass) and hover lift. Styles live in
// tokens.css; `hue` feeds --panel-hue so each panel can glow its own color
// (the multi-hue rule: panels stop inheriting one global accent).
import type { HTMLAttributes } from "react";

interface GlassProps extends HTMLAttributes<HTMLDivElement> {
  /** brighter fill for hero surfaces */
  strong?: boolean;
  /** neon edge stroke + glow — reserve for interactive glass */
  neon?: boolean;
  /** lifts on hover (adds the §3.3 card affordance) */
  lift?: boolean;
  /** CSS color for this panel's glow; defaults to the dominant accent */
  hue?: string;
}

export function Glass({
  strong,
  neon,
  lift,
  hue,
  className = "",
  style,
  children,
  ...rest
}: GlassProps) {
  const cls = [
    "glass",
    strong ? "glass-strong" : "",
    neon ? "glass-neon" : "",
    lift ? "hover-lift" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const styles = hue
    ? ({ ...style, "--panel-hue": hue } as React.CSSProperties)
    : style;
  return (
    <div className={cls} style={styles} {...rest}>
      {children}
    </div>
  );
}
