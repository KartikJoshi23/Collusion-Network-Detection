import { motion } from "motion/react";
import type { Domain } from "../api/types";
import { useConsole } from "../state/console";

// V3 §5: each domain pill carries its own two-hue ramp (§5.2 accent ramps) —
// the toggle itself is multi-hue at rest instead of accent-dim.
const DOMAINS: { id: Domain; label: string; from: string; to: string }[] = [
  { id: "financial", label: "Financial", from: "var(--hue-cyan)", to: "var(--hue-teal)" },
  { id: "procurement", label: "Procurement", from: "var(--hue-violet)", to: "var(--hue-magenta)" },
];

// The domain toggle recolors the whole console (§5.2): flipping it swaps the
// accent ramp via data-domain on <html>; the active pill slides via layoutId.
export function DomainToggle() {
  const domain = useConsole((s) => s.domain);
  const setDomain = useConsole((s) => s.setDomain);
  return (
    <div
      className="inline-flex rounded-lg p-0.5"
      style={{
        background: "var(--glass-fill)",
        boxShadow: "inset 0 0 0 1px var(--hairline)",
      }}
    >
      {DOMAINS.map((d) => {
        const active = d.id === domain;
        return (
          <button
            key={d.id}
            onClick={() => setDomain(d.id)}
            className="relative rounded-md px-3 py-1 text-xs font-medium transition-colors"
            style={{ color: active ? d.from : "var(--text-1)" }}
          >
            {active && (
              <motion.span
                layoutId="domain-active"
                className="absolute inset-0 rounded-md"
                style={{
                  background: `linear-gradient(110deg, color-mix(in srgb, ${d.from} 20%, transparent), color-mix(in srgb, ${d.to} 14%, transparent))`,
                  boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${d.from} 40%, transparent), 0 0 14px -4px color-mix(in srgb, ${d.to} 55%, transparent)`,
                }}
                transition={{ type: "spring", stiffness: 550, damping: 40 }}
              />
            )}
            <span className="relative">{d.label}</span>
          </button>
        );
      })}
    </div>
  );
}
