// V3 Copilot identity (docs/frontend_overhaul.md V3 §3): an orbital-spark
// logo — gradient ring, spark core, one orbiting electron. The mark breathes
// when idle and the orbit spins; both collapse under prefers-reduced-motion
// (CSS-driven, see tokens.css `.copilot-mark`).
export function CopilotMark({
  size = 18,
  active = false,
}: {
  size?: number;
  active?: boolean;
}) {
  return (
    <span
      className={`copilot-mark ${active ? "copilot-mark-active" : ""}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" width={size} height={size}>
        <defs>
          <linearGradient id="cg-copilot-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--hue-magenta)" />
            <stop offset="55%" stopColor="var(--hue-violet)" />
            <stop offset="100%" stopColor="var(--hue-cyan)" />
          </linearGradient>
        </defs>
        {/* orbit ring */}
        <ellipse
          cx="12"
          cy="12"
          rx="10"
          ry="5.6"
          fill="none"
          stroke="url(#cg-copilot-ring)"
          strokeWidth="1.5"
          transform="rotate(-24 12 12)"
        />
        {/* spark core — a four-point star */}
        <path
          d="M12 6.6c.7 3 1.6 3.9 4.6 4.6-3 .7-3.9 1.6-4.6 4.6-.7-3-1.6-3.9-4.6-4.6 3-.7 3.9-1.6 4.6-4.6Z"
          fill="var(--hue-magenta)"
        />
        {/* orbiting electron (CSS animates the group rotation) */}
        <g className="copilot-electron">
          <circle cx="21.2" cy="8.4" r="1.7" fill="var(--hue-cyan)" />
        </g>
      </svg>
    </span>
  );
}
