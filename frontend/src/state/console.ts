// Console state (§5.1): domain, dataset, budget k, current alert selection.
import { create } from "zustand";
import type { Domain } from "../api/types";

export type ViewId =
  | "overview"
  | "queue"
  | "explorer"
  | "case"
  | "lab";

interface ConsoleState {
  domain: Domain;
  dataset: string | undefined;
  budget: number;
  selectedAlertId: string | undefined;
  view: ViewId;
  setDomain: (d: Domain) => void;
  setDataset: (d: string | undefined) => void;
  setBudget: (k: number) => void;
  selectAlert: (id: string | undefined) => void;
  setView: (v: ViewId) => void;
}

export const useConsole = create<ConsoleState>((set) => ({
  domain: "financial",
  dataset: undefined,
  budget: 50,
  selectedAlertId: undefined,
  view: "overview",
  setDomain: (domain) =>
    set({ domain, dataset: undefined, selectedAlertId: undefined }),
  setDataset: (dataset) => set({ dataset, selectedAlertId: undefined }),
  setBudget: (budget) => set({ budget }),
  selectAlert: (selectedAlertId) => set({ selectedAlertId }),
  setView: (view) => set({ view }),
}));

// Keep the document's data-domain in sync so the token layer recolors (§5.2).
useConsole.subscribe((s) => {
  document.documentElement.dataset.domain = s.domain;
});
