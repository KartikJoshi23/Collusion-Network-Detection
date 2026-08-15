// Defensive extraction over the Phase-2 rigor artifact payloads (§7 steps
// 28–29, 32). Values are COPIED from the artifacts, never re-derived — the
// eval harness is the single source of truth for every number shown.

type Obj = Record<string, unknown>;

const num = (v: unknown): number | null => (typeof v === "number" ? v : null);

export interface SeedAggregate {
  label: string;
  mean: number;
  std: number;
  perSeed: number[];
}

// multiseed.json — {aggregate: {auc_pr_mean, auc_pr_std}, per_seed: [{auc_pr}]}
export function parseMultiseed(payload: Obj, label: string): SeedAggregate | null {
  const agg = payload.aggregate as Obj | undefined;
  const mean = num(agg?.auc_pr_mean);
  const std = num(agg?.auc_pr_std);
  if (mean === null || std === null) return null;
  const perSeed = Array.isArray(payload.per_seed)
    ? (payload.per_seed as Obj[]).map((r) => num(r.auc_pr)).filter((v): v is number => v !== null)
    : [];
  return { label, mean, std, perSeed };
}

// ensemble_multiseed.json — {members: {name: {auc_pr_mean, auc_pr_std, auc_pr_per_seed}}}
export function parseEnsembleMultiseed(payload: Obj): SeedAggregate[] {
  const members = payload.members as Record<string, Obj> | undefined;
  if (!members) return [];
  const out: SeedAggregate[] = [];
  for (const [name, m] of Object.entries(members)) {
    const mean = num(m.auc_pr_mean);
    const std = num(m.auc_pr_std);
    if (mean === null || std === null) continue;
    const perSeed = Array.isArray(m.auc_pr_per_seed)
      ? (m.auc_pr_per_seed as unknown[]).filter((v): v is number => typeof v === "number")
      : [];
    out.push({ label: name, mean, std, perSeed });
  }
  return out.sort((a, b) => b.mean - a.mean);
}

export interface MatrixFold {
  group: string;
  val: string;
  n: number;
  prevalence: number;
  mean: number;
  std: number;
  lift: number;
}

// matrix.json — {folds: [{test_group, val_group, status, n_confirmed_test,
// prevalence_baseline, auc_pr_mean, auc_pr_std, lift_mean}], summary: {...}}
export function parseTransferMatrix(payload: Obj): {
  folds: MatrixFold[];
  macroLift: number | null;
} {
  const folds: MatrixFold[] = [];
  if (Array.isArray(payload.folds)) {
    for (const f of payload.folds as Obj[]) {
      if (f.status !== "completed") continue;
      const mean = num(f.auc_pr_mean);
      const prevalence = num(f.prevalence_baseline);
      if (mean === null || prevalence === null) continue;
      folds.push({
        group: String(f.test_group ?? "?"),
        val: String(f.val_group ?? "?"),
        n: num(f.n_confirmed_test) ?? 0,
        prevalence,
        mean,
        std: num(f.auc_pr_std) ?? 0,
        lift: num(f.lift_mean) ?? 0,
      });
    }
  }
  const summary = payload.summary as Obj | undefined;
  return { folds, macroLift: num(summary?.macro_lift_mean) };
}

export interface SignificanceRow {
  name: string;
  labelA: string;
  labelB: string;
  aucA: number;
  aucB: number;
  delta: number;
  ciLow: number;
  ciHigh: number;
  p: number;
}

// significance.json — {comparisons: {name: {label_a, label_b, auc_pr_a,
// auc_pr_b, delta, delta_ci_low, delta_ci_high, p_value}}}
export function parseSignificance(payload: Obj): SignificanceRow[] {
  const comparisons = payload.comparisons as Record<string, Obj> | undefined;
  if (!comparisons) return [];
  const out: SignificanceRow[] = [];
  for (const [name, c] of Object.entries(comparisons)) {
    const delta = num(c.delta);
    const p = num(c.p_value);
    if (delta === null || p === null) continue;
    out.push({
      name,
      labelA: String(c.label_a ?? "A"),
      labelB: String(c.label_b ?? "B"),
      aucA: num(c.auc_pr_a) ?? 0,
      aucB: num(c.auc_pr_b) ?? 0,
      delta,
      ciLow: num(c.delta_ci_low) ?? 0,
      ciHigh: num(c.delta_ci_high) ?? 0,
      p,
    });
  }
  return out;
}

export interface CurvePoint {
  k: number;
  value: number;
  std?: number;
}

// noise_curve.json — {curve: [{rate, auc_pr_mean, auc_pr_std}]}; x = rate in %
export function parseNoiseCurve(payload: Obj): CurvePoint[] {
  if (!Array.isArray(payload.curve)) return [];
  const out: CurvePoint[] = [];
  for (const c of payload.curve as Obj[]) {
    const rate = num(c.rate);
    const mean = num(c.auc_pr_mean);
    if (rate === null || mean === null) continue;
    out.push({ k: Math.round(rate * 100), value: mean, std: num(c.auc_pr_std) ?? undefined });
  }
  return out.sort((a, b) => a.k - b.k);
}

// label_efficiency.json — {curve: [{k, status, source_probe_auc_pr_mean,
// raw_probe_auc_pr_mean, transfer_gain_mean}], full_label_reference: {...}}
// The absolute source-probe curve plots in [0,1]; gains (which go negative)
// render as text, never on the shared [0,1]-domain chart.
export function parseLabelEfficiency(payload: Obj): {
  source: CurvePoint[];
  gain: CurvePoint[];
  reference: { source: number; raw: number } | null;
} {
  const source: CurvePoint[] = [];
  const gain: CurvePoint[] = [];
  if (Array.isArray(payload.curve)) {
    for (const c of payload.curve as Obj[]) {
      if (c.status && c.status !== "completed") continue;
      const k = num(c.k);
      const s = num(c.source_probe_auc_pr_mean);
      const g = num(c.transfer_gain_mean);
      if (k === null) continue;
      if (s !== null) source.push({ k, value: s });
      if (g !== null) gain.push({ k, value: g });
    }
  }
  const ref = payload.full_label_reference as Obj | undefined;
  const refSource = num(ref?.source_probe_auc_pr);
  const refRaw = num(ref?.raw_probe_auc_pr);
  return {
    source: source.sort((a, b) => a.k - b.k),
    gain: gain.sort((a, b) => a.k - b.k),
    reference: refSource !== null && refRaw !== null ? { source: refSource, raw: refRaw } : null,
  };
}

export interface SensitivitySummary {
  nGrid: number;
  keptValues: number[];
  hitsMin: number;
  hitsMax: number;
}

// sensitivity.json — {results: [{jaccard_threshold, min_fraction, n_kept,
// n_hits_total, ...}]}
export function parseSensitivity(payload: Obj): SensitivitySummary | null {
  if (!Array.isArray(payload.results) || payload.results.length === 0) return null;
  const rows = payload.results as Obj[];
  const kept = [...new Set(rows.map((r) => num(r.n_kept) ?? -1))].sort((a, b) => a - b);
  const hits = rows.map((r) => num(r.n_hits_total) ?? 0);
  return {
    nGrid: rows.length,
    keptValues: kept,
    hitsMin: Math.min(...hits),
    hitsMax: Math.max(...hits),
  };
}
