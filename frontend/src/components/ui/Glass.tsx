// Glass panel primitive (§5.2 depth & texture): translucent fill, backdrop
// blur, 1px gradient border, inner top-light. Styles live in tokens.css so
// the same look is reachable from plain markup via className="glass".
import type { HTMLAttributes } from "react";

interface GlassProps extends HTMLAttributes<HTMLDivElement> {
  /** brighter fill for hero surfaces */
  strong?: boolean;
  /** accent halo — reserve for the surfaces that should draw the eye */
  glow?: boolean;
}

export function Glass({
  strong,
  glow,
  className = "",
  children,
  ...rest
}: GlassProps) {
  const cls = [
    "glass",
    strong ? "glass-strong" : "",
    glow ? "glass-glow" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
