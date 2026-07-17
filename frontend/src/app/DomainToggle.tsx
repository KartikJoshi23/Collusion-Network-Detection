import type { Domain } from "../api/types";
import { useConsole } from "../state/console";

const DOMAINS: { id: Domain; label: string }[] = [
  { id: "financial", label: "Financial" },
  { id: "procurement", label: "Procurement" },
];

export function DomainToggle() {
  const domain = useConsole((s) => s.domain);
  const setDomain = useConsole((s) => s.setDomain);
  return (
    <div className="inline-flex rounded-lg border border-hairline bg-bg-1 p-0.5">
      {DOMAINS.map((d) => {
        const active = d.id === domain;
        return (
          <button
            key={d.id}
            onClick={() => setDomain(d.id)}
            className="rounded-md px-3 py-1 text-xs font-medium transition-colors"
            style={{
              background: active ? "var(--accent-dim)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-1)",
            }}
          >
            {d.label}
          </button>
        );
      })}
    </div>
  );
}
