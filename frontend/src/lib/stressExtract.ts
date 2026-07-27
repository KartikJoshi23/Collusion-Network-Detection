// Defensive normaliser for the injection-recovery artifact (§7 step 30).
// Two on-disk shapes exist — a single-seed report and a multi-seed aggregate —
// and the tab must render either. Values are COPIED from the artifact, never
// re-derived; "recovered" per shape is the BEST arm's recall at that budget
// (the same reading the report headlines, since different shapes are caught by
// different detectors).

type Obj = Record<string, unknown>;

const num = (v: unknown): number | null => (typeof v === "number" ? v : null);

export interface ShapeRecovery {
  motif: string;
  nMembers: number;
  // budget → { recall (mean), std, arm that achieved it }
  byBudget: Record<number, { recall: number; std: number; arm: string }>;
}

export interface StressModel {
  population: number;
  nInstances: number | null;
  nMembers: number | null;
  nSeeds: number;
  budgets: number[];
  shapes: ShapeRecovery[];
}

function budgetOf(key: string): number | null {
  const m = /^recall@(\d+)$/.exec(key);
  return m ? Number(m[1]) : null;
}

// Merge one (arm, motif, budget, recall, std) observation, keeping the best.
function keepBest(
  acc: Map<string, ShapeRecovery>,
  motif: string,
  nMembers: number,
  budget: number,
  recall: number,
  std: number,
  arm: string,
): void {
  let shape = acc.get(motif);
  if (!shape) {
    shape = { motif, nMembers, byBudget: {} };
    acc.set(motif, shape);
  }
  const cur = shape.byBudget[budget];
  if (!cur || recall > cur.recall) shape.byBudget[budget] = { recall, std, arm };
}

export function parseStress(payload: Obj): StressModel | null {
  const population = num(payload.population);
  if (population === null) return null;
  const acc = new Map<string, ShapeRecovery>();
  const budgets = new Set<number>();

  const multi = payload.recovery_multiseed as Record<string, Obj> | undefined;
  const single = payload.recovery as Record<string, Obj[]> | undefined;

  if (multi) {
    for (const [arm, motifs] of Object.entries(multi)) {
      for (const [motif, entry] of Object.entries(motifs as Obj)) {
        const e = entry as Obj;
        const nMembers = num(e.n_members) ?? 0;
        for (const [k, v] of Object.entries(e)) {
          const budget = budgetOf(k);
          if (budget === null) continue;
          const mean = num((v as Obj)?.mean);
          if (mean === null) continue;
          budgets.add(budget);
          keepBest(acc, motif, nMembers, budget, mean, num((v as Obj).std) ?? 0, arm);
        }
      }
    }
  } else if (single) {
    for (const [arm, rows] of Object.entries(single)) {
      for (const row of rows) {
        const motif = String(row.motif_type ?? "?");
        const nMembers = num(row.n_members) ?? 0;
        for (const [k, v] of Object.entries(row)) {
          const budget = budgetOf(k);
          if (budget === null) continue;
          const recall = num(v);
          if (recall === null) continue;
          budgets.add(budget);
          keepBest(acc, motif, nMembers, budget, recall, 0, arm);
        }
      }
    }
  } else {
    return null;
  }

  const budgetList = [...budgets].sort((a, b) => a - b);
  const topBudget = budgetList[budgetList.length - 1];
  const shapes = [...acc.values()].sort(
    (a, b) => (b.byBudget[topBudget]?.recall ?? 0) - (a.byBudget[topBudget]?.recall ?? 0),
  );
  const seeds = Array.isArray(payload.seeds) ? (payload.seeds as unknown[]).length : 1;

  return {
    population,
    nInstances: num(payload.n_injected_instances),
    nMembers: num(payload.n_injected_members),
    nSeeds: seeds,
    budgets: budgetList,
    shapes,
  };
}
