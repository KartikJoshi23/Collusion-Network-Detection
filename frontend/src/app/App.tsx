import { MotionConfig, motion } from "motion/react";
import { SCREENING_CAVEAT } from "../api/types";
import { AuroraGL } from "../components/bg/AuroraGL";
import { NetworkBackground } from "../components/bg/NetworkBackground";
import { CopilotDock } from "../components/copilot/CopilotDock";
import { CopilotMark } from "../components/copilot/CopilotMark";
import { ViewIcon } from "../components/ui/ViewIcons";
import { UI_HUES } from "../lib/palette";
import { useConsole, type ViewId } from "../state/console";
import { DatasetSelector } from "./DatasetSelector";
import { DomainToggle } from "./DomainToggle";
import { ViewRouter } from "./ViewRouter";

// V3 (docs/frontend_overhaul.md V3 §2): every view carries a FIXED hue
// identity — tab ink, active pill, underglow, and the view's H1 gradient all
// take it, so the console is multi-hue at rest in both domains. Coral is
// flagged-exclusive (§5.2) and never a tab hue.
const NAV: { id: ViewId; label: string; hue: string }[] = [
  { id: "overview", label: "Overview", hue: UI_HUES.cyan },
  { id: "queue", label: "Alert Queue", hue: UI_HUES.amber },
  { id: "explorer", label: "Graph Explorer", hue: UI_HUES.teal },
  { id: "case", label: "Case Detail", hue: UI_HUES.magenta },
  { id: "lab", label: "Model Lab", hue: UI_HUES.violet },
  { id: "about", label: "About", hue: "#94a3c2" },
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
  const copilotOpen = useConsole((s) => s.copilotOpen);
  const toggleCopilot = useConsole((s) => s.toggleCopilot);
  const viewHue = NAV.find((n) => n.id === view)?.hue ?? UI_HUES.cyan;

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative flex h-full flex-col">
        <AuroraGL />
        <NetworkBackground />

        <header className="glass z-10 m-2 mb-0">
          <div className="flex items-center gap-4 px-4 py-2">
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
              <span className="hidden text-xs text-text-2 xl:inline">
                Integrity Screening Console
              </span>
            </div>

            <nav className="tabbar ml-2" role="tablist" aria-label="console views">
              {NAV.map((n) => {
                const active = view === n.id;
                return (
                  <button
                    key={n.id}
                    role="tab"
                    aria-selected={active}
                    onClick={() => setView(n.id)}
                    className="tab"
                    style={{ "--tab-hue": n.hue } as React.CSSProperties}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-active"
                        className="tab-pill"
                        transition={{ type: "spring", stiffness: 550, damping: 40 }}
                      />
                    )}
                    <span className="relative inline-flex items-center gap-1.5">
                      <ViewIcon view={n.id} />
                      <span className="hidden lg:inline">{n.label}</span>
                    </span>
                  </button>
                );
              })}
            </nav>

            <div className="ml-auto flex items-center gap-3">
              <DatasetSelector />
              <DomainToggle />
              <button
                onClick={toggleCopilot}
                title="Investigator Copilot — tool-grounded Q&A over the served queues"
                className="btn-sheen inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium"
                style={{
                  color: copilotOpen ? "var(--hue-magenta)" : "var(--text-1)",
                  background: copilotOpen
                    ? "color-mix(in srgb, var(--hue-magenta) 14%, transparent)"
                    : "var(--glass-fill-lo)",
                  boxShadow: copilotOpen
                    ? "inset 0 0 0 1px color-mix(in srgb, var(--hue-magenta) 35%, transparent)"
                    : "inset 0 0 0 1px var(--hairline)",
                }}
              >
                <CopilotMark size={17} active={copilotOpen} />
                Copilot
              </button>
            </div>
          </div>
          <div className="hue-underline" aria-hidden />
        </header>

        <div className="z-0 flex min-h-0 flex-1 overflow-hidden">
          <main
            className="min-h-0 min-w-0 flex-1 overflow-hidden p-2"
            style={
              {
                // every .text-grad inside the active view takes the view hue
                "--accent-grad": `linear-gradient(120deg, ${viewHue}, var(--accent-2))`,
                "--view-hue": viewHue,
              } as React.CSSProperties
            }
          >
            <ViewRouter />
          </main>
          <CopilotDock />
        </div>

        <footer
          className="z-10 flex items-center justify-center gap-2 px-4 pb-2 pt-0.5 text-center text-xs"
          style={{ color: "color-mix(in srgb, var(--benign) 45%, var(--text-2))" }}
        >
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
