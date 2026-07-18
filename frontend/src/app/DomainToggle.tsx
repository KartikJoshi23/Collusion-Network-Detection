import { motion } from "motion/react";
import type { Domain } from "../api/types";
import { useConsole } from "../state/console";

const DOMAINS: { id: Domain; label: string }[] = [
  { id: "financial", label: "Financial" },
  { id: "procurement", label: "Procurement" },
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
            style={{ color: active ? "var(--accent)" : "var(--text-1)" }}
          >
            {active && (
              <motion.span
                layoutId="domain-active"
                className="absolute inset-0 rounded-md"
                style={{
                  background: "var(--accent-dim)",
                  boxShadow:
                    "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
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
