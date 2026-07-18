// Pure extractors turning published metrics.json runs into chart series
// (tested). Charts render ONLY what a run measured — no interpolation.

export interface StepPoint {
  step: number;
  aucPr: number;
  prevalence: number | null;
}

export interface KPoint {
  k: number;
  value: number;
}

type Obj = Record<string, unknown>;

export function parsePerTimeStep(nodeLevel: Obj | undefined): StepPoint[] {
  const pts = nodeLevel?.per_time_step as Obj | undefined;
  if (!pts) return [];
  return Object.entries(pts)
    .map(([step, v]) => {
      const o = v as Obj;
      return {
        step: Number(step),
        aucPr: Number(o.auc_pr),
        prevalence:
          typeof o.prevalence_baseline === "number"
            ? o.prevalence_baseline
            : null,
      };
    })
    .filter((p) => Number.isFinite(p.step) && Number.isFinite(p.aucPr))
    .sort((a, b) => a.step - b.step);
}

/** precision@k / recall@k style keys → sorted [{k, value}]. */
export function parseAtK(level: Obj | undefined, prefix: string): KPoint[] {
  if (!level) return [];
  const out: KPoint[] = [];
  for (const [key, v] of Object.entries(level)) {
    const m = key.match(new RegExp(`^${prefix}@(\\d+)$`));
    if (m && typeof v === "number") out.push({ k: Number(m[1]), value: v });
  }
  return out.sort((a, b) => a.k - b.k);
}

/** alert_level.queue {"@50": {precision, …}} → sorted [{k, value}]. */
export function parseQueue(alertLevel: Obj | undefined): KPoint[] {
  const queue = alertLevel?.queue as Obj | undefined;
  if (!queue) return [];
  const out: KPoint[] = [];
  for (const [key, v] of Object.entries(queue)) {
    const m = key.match(/^@(\d+)$/);
    const p = (v as Obj)?.precision;
    if (m && typeof p === "number") out.push({ k: Number(m[1]), value: p });
  }
  return out.sort((a, b) => a.k - b.k);
}
