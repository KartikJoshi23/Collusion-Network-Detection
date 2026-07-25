import { motion } from "motion/react";
import type { Domain } from "../api/types";
import { useConsole } from "../state/console";

// V3 §5: each domain pill carries its own two-hue ramp (§5.2 accent ramps) —
// the toggle itself is multi-hue at rest instead of accent-dim.
// `sub` names the actual crime. "Financial" and "Procurement" alone never told
// anyone that this side is anti-money-laundering screening — an audit found the
// letters "AML" appeared nowhere in the console outside two buried About lines.
const DOMAINS: {
  id: Domain;
  label: string;
  sub: string;
  title: string;
  from: string;
  to: string;
}[] = [
  {
    id: "financial",
    label: "Financial",
    sub: "AML",
    title:
      "Anti-money-laundering screening — criminal funds moved through many accounts to look legitimate. Alerts cite FATF indicators.",
    from: "var(--hue-cyan)",
    to: "var(--hue-teal)",
  },
  {
    id: "procurement",
    label: "Procurement",
    sub: "bid rigging",
    title:
      "Bid-rigging screening — firms that should compete for public contracts secretly agreeing who wins. Alerts cite OECD indicators.",
    from: "var(--hue-violet)",
    to: "var(--hue-magenta)",
  },
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
            title={d.title}
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
            <span className="relative inline-flex items-baseline gap-1">
              <span>{d.label}</span>
              <span
                className="text-[10px] font-normal"
                style={{ color: active ? d.to : "var(--text-2)" }}
              >
                · {d.sub}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
