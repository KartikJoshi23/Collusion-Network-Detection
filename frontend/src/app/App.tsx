import { SCREENING_CAVEAT } from "../api/types";
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

export function App() {
  const view = useConsole((s) => s.view);
  const setView = useConsole((s) => s.setView);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-4 border-b border-hairline bg-bg-1 px-4 py-2">
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-4 w-4 rounded-sm"
            style={{
              background: "var(--accent)",
              boxShadow: "0 0 12px var(--accent)",
            }}
          />
          <span className="text-sm font-semibold tracking-tight">
            CollusionGraph
          </span>
          <span className="text-xs text-text-2">Integrity Screening Console</span>
        </div>

        <nav className="ml-4 flex items-center gap-1">
          {NAV.map((n) => (
            <button
              key={n.id}
              onClick={() => setView(n.id)}
              className="rounded-md px-2.5 py-1 text-xs transition-colors"
              style={{
                background: view === n.id ? "var(--bg-3)" : "transparent",
                color: view === n.id ? "var(--text-0)" : "var(--text-1)",
              }}
            >
              {n.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <DatasetSelector />
          <DomainToggle />
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-hidden">
        <ViewRouter />
      </main>

      <footer className="border-t border-hairline bg-bg-1 px-4 py-1.5 text-center text-xs text-text-2">
        {SCREENING_CAVEAT}
      </footer>
    </div>
  );
}
