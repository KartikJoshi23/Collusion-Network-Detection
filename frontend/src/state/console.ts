// Console state (§5.1): domain, dataset, budget k, current alert selection.
import { create } from "zustand";
import type { Domain } from "../api/types";

export type ViewId =
  | "overview"
  | "queue"
  | "explorer"
  | "case"
  | "lab"
  | "stress"
  | "about";

interface ConsoleState {
  domain: Domain;
  dataset: string | undefined;
  budget: number;
  selectedAlertId: string | undefined;
  view: ViewId;
  copilotOpen: boolean;
  copilotSeed: string | undefined; // alert id the dock is contextualised with
  copilotPrefill: string | undefined; // a question to drop into the dock input
  setDomain: (d: Domain) => void;
  setDataset: (d: string | undefined) => void;
  hydrateFromAlert: (domain: Domain, dataset: string) => void;
  setBudget: (k: number) => void;
  selectAlert: (id: string | undefined) => void;
  setView: (v: ViewId) => void;
  toggleCopilot: () => void;
  askCopilotAbout: (alertId: string) => void;
  askCopilot: (question: string) => void; // open the dock with a suggested question
  consumeCopilotPrefill: () => void;
  clearCopilotSeed: () => void;
}

const VIEW_IDS: ViewId[] = [
  "overview",
  "queue",
  "explorer",
  "case",
  "lab",
  "stress",
  "about",
];

// Deep-link support (demo script §5.4): /?view=explorer&alert=<id> opens the
// console directly on a view / alert.
function initialFromUrl(): { view: ViewId; alert: string | undefined } {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view") as ViewId | null;
  return {
    view: view && VIEW_IDS.includes(view) ? view : "overview",
    alert: params.get("alert") ?? undefined,
  };
}

const initial = initialFromUrl();

export const useConsole = create<ConsoleState>((set) => ({
  domain: "financial",
  dataset: undefined,
  budget: 50,
  selectedAlertId: initial.alert,
  view: initial.view,
  copilotOpen: false,
  copilotSeed: undefined,
  copilotPrefill: undefined,
  setDomain: (domain) =>
    set({ domain, dataset: undefined, selectedAlertId: undefined }),
  // Switching datasets clears the selection; the INITIAL auto-select (dataset
  // undefined → first) must not, or deep-linked alerts would be wiped.
  setDataset: (dataset) =>
    set((s) => ({
      dataset,
      selectedAlertId: s.dataset === undefined ? s.selectedAlertId : undefined,
    })),
  // One-shot deep-link hydration: adopt the linked alert's own dataset and
  // domain (lib/deeplink.ts) WITHOUT clearing the selection — setDomain would.
  hydrateFromAlert: (domain, dataset) => set({ domain, dataset }),
  setBudget: (budget) => set({ budget }),
  selectAlert: (selectedAlertId) => set({ selectedAlertId }),
  setView: (view) => set({ view }),
  toggleCopilot: () => set((s) => ({ copilotOpen: !s.copilotOpen })),
  // §5.3 view 7 context-seeding: opened from an alert, the dock carries that
  // alert's id so "explain this" resolves without retyping
  askCopilotAbout: (alertId) => set({ copilotOpen: true, copilotSeed: alertId }),
  // Open the dock carrying a suggested question (the dock drops it into its
  // input on open); used by the Stress Test tab's "Ask the Copilot" button.
  askCopilot: (question) => set({ copilotOpen: true, copilotPrefill: question }),
  consumeCopilotPrefill: () => set({ copilotPrefill: undefined }),
  clearCopilotSeed: () => set({ copilotSeed: undefined }),
}));

// Keep the document's data-domain in sync so the token layer recolors (§5.2).
useConsole.subscribe((s) => {
  document.documentElement.dataset.domain = s.domain;
});
