import { MotionConfig, motion } from "motion/react";
import { SCREENING_CAVEAT } from "../api/types";
import { NetworkBackground } from "../components/bg/NetworkBackground";
import { useConsole, type ViewId } from "../state/console";
import { DatasetSelector } from "./DatasetSelector";
import { DomainToggle } from "./DomainToggle";
import { ViewRouter } from "./ViewRouter";

const NAV: { id: ViewId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "queue", label: "Alert Queue" },
  { id: "explorer", label: "Graph Explorer" },
  { id: "case", label: "Case Detail" },
  { id: "lab", label: "Model Lab" },
];

// The console mark: three linked nodes, one flagged — the project in 18px.
function Mark() {
  return (
    <svg viewBox="0 0 32 32" width="18" height="18" aria-hidden>
      <g fill="none" strokeWidth="2.4">
        <path
          d="M9 23L14 10M18 10L23 20M10 24.5L22 22.5"
          stroke="var(--accent)"
          opacity="0.75"
        />
        <circle cx="7" cy="25" r="3.4" fill="var(--accent)" />
        <circle cx="16" cy="8" r="3.4" fill="var(--accent-2)" />
        <circle cx="25" cy="22" r="3.4" fill="var(--risk-high)" />
      </g>
    </svg>
  );
}

export function App() {
  const view = useConsole((s) => s.view);
  const setView = useConsole((s) => s.setView);

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative flex h-full flex-col">
        <NetworkBackground />

        <header className="glass z-10 m-2 mb-0 flex items-center gap-4 px-4 py-2">
          <div className="flex items-center gap-2.5">
            <span
              className="grid h-7 w-7 place-items-center rounded-lg"
              style={{
                background: "var(--accent-dim)",
                boxShadow: "0 0 18px -2px var(--accent)",
              }}
            >
              <Mark />
            </span>
            <span className="display text-[15px] font-semibold tracking-tight">
              Collusion<span className="text-grad">Graph</span>
            </span>
            <span className="hidden text-xs text-text-2 sm:inline">
              Integrity Screening Console
            </span>
          </div>

          <nav className="ml-2 flex items-center gap-1">
            {NAV.map((n) => {
              const active = view === n.id;
              return (
                <button
                  key={n.id}
                  onClick={() => setView(n.id)}
                  className="relative rounded-md px-2.5 py-1 text-xs transition-colors"
                  style={{ color: active ? "var(--text-0)" : "var(--text-1)" }}
                >
                  {active && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-md"
                      style={{
                        background: "var(--accent-dim)",
                        boxShadow:
                          "inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)",
                      }}
                      transition={{ type: "spring", stiffness: 550, damping: 40 }}
                    />
                  )}
                  <span className="relative">{n.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <DatasetSelector />
            <DomainToggle />
          </div>
        </header>

        <main className="z-0 min-h-0 flex-1 overflow-hidden p-2">
          <ViewRouter />
        </main>

        <footer className="z-10 flex items-center justify-center gap-2 px-4 pb-2 pt-0.5 text-center text-xs text-text-2">
          <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden>
            <path
              d="M8 1.5 13.5 4v3.8c0 3.4-2.3 5.7-5.5 6.7-3.2-1-5.5-3.3-5.5-6.7V4L8 1.5Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
            />
          </svg>
          {SCREENING_CAVEAT}
        </footer>
      </div>
    </MotionConfig>
  );
}
