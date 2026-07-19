import { motion } from "motion/react";
import { useRigor } from "../../api/hooks";
import { ChartCard } from "../../components/charts/ChartCard";
import { AtKChart } from "../../components/charts/Charts";
import { Glass } from "../../components/ui/Glass";
import {
  parseEnsembleMultiseed,
  parseLabelEfficiency,
  parseMultiseed,
  parseNoiseCurve,
  parseSensitivity,
  parseSignificance,
  parseTransferMatrix,
  type SeedAggregate,
} from "../../lib/rigorExtract";
import { CHART_SERIES, UI_HUES } from "../../lib/palette";

// §7 steps 28–29/32 rigor artifacts rendered into the Model Lab (§5.3 view 5):
// multi-seed uncertainty, transfer matrices, significance tests, robustness
// curves. Every number is copied from a published artifact — nothing is
// computed in the browser. Absent artifacts simply don't render (a thin
// machine's console stays honest). Negative/failing values read amber —
// coral stays exclusive to flagged entities (§5.2).
export function RigorSection({ dataset }: { dataset: string }) {
  const { data } = useRigor(dataset);
  if (!data) return null;
  const a = data.artifacts;

  const seedAggs: SeedAggregate[] = [];
  for (const [name, label] of [
    ["multiseed_gatv2", "GATv2-focal (raw)"],
    ["multiseed_rgcn", "R-GCN (structural)"],
  ] as const) {
    const payload = a[name]?.payload;
    if (payload) {
      const agg = parseMultiseed(payload, label);
      if (agg) seedAggs.push(agg);
    }
  }
  const ensembleAggs = a.multiseed_ensemble?.payload
    ? parseEnsembleMultiseed(a.multiseed_ensemble.payload)
    : [];
  const significance = a.significance?.payload
    ? parseSignificance(a.significance.payload)
    : [];
  const matrices = (
    [
      ["loco_matrix", "LOCO matrix — Mendeley (7 countries × 5 seeds)"],
      ["lomo_matrix_garcia", "LOMO matrix — García (4 markets × 5 seeds)"],
    ] as const
  )
    .filter(([name]) => a[name]?.payload)
    .map(([name, title]) => ({ name, title, ...parseTransferMatrix(a[name]!.payload) }));
  const noise = a.label_noise?.payload ? parseNoiseCurve(a.label_noise.payload) : [];
  const efficiency = a.label_efficiency?.payload
    ? parseLabelEfficiency(a.label_efficiency.payload)
    : null;
  const sensitivity = a.sensitivity?.payload
    ? parseSensitivity(a.sensitivity.payload)
    : null;

  const hasAnything =
    seedAggs.length + ensembleAggs.length + significance.length + matrices.length > 0 ||
    noise.length > 0 ||
    (efficiency?.gain.length ?? 0) > 0 ||
    sensitivity !== null;
  if (!hasAnything) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="grid gap-3"
    >
      <div className="px-2 pt-2">
        <h3 className="display text-base font-semibold">
          Rigor <span className="text-grad">&amp; Uncertainty</span>
        </h3>
        <p className="text-xs text-text-2">
          Multi-seed spread, transfer matrices, significance and robustness —
          published Phase-2 artifacts, shown as measured.
        </p>
      </div>

      {(seedAggs.length > 0 || ensembleAggs.length > 0) && (
        <div className="flex flex-wrap gap-2 px-2">
          {[...seedAggs, ...ensembleAggs.map((m) => ({ ...m, label: `ensemble: ${m.label}` }))].map(
            (agg) => (
              <div
                key={agg.label}
                className="hover-lift min-w-44 rounded-md px-3 py-2"
                style={{
                  background: "var(--bg-2)",
                  boxShadow: "inset 0 0 0 1px var(--hairline)",
                }}
              >
                <div className="text-[10px] uppercase tracking-wide text-text-2">
                  {agg.label} · {agg.perSeed.length || "?"} seeds
                </div>
                <div className="mono text-sm" style={{ color: UI_HUES.cyan }}>
                  {agg.mean.toFixed(4)}{" "}
                  <span className="text-text-2">± {agg.std.toFixed(4)}</span>
                </div>
                {agg.perSeed.length > 0 && (
                  <div className="mono mt-0.5 text-[10px] text-text-2">
                    {agg.perSeed.map((v) => v.toFixed(3)).join(" · ")}
                  </div>
                )}
              </div>
            ),
          )}
        </div>
      )}

      {significance.length > 0 && (
        <Glass className="mx-2 p-3">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-text-2">
            Paired bootstrap significance (2,000 resamples, stratified)
          </div>
          <div className="grid gap-1">
            {significance.map((row) => (
              <div key={row.name} className="mono text-xs text-text-1">
                <span className="text-text-0">{row.labelA}</span> vs{" "}
                <span className="text-text-0">{row.labelB}</span>: Δ AUC-PR{" "}
                <span style={{ color: row.delta >= 0 ? UI_HUES.teal : UI_HUES.amber }}>
                  {row.delta >= 0 ? "+" : ""}
                  {row.delta.toFixed(3)}
                </span>{" "}
                [{row.ciLow.toFixed(3)}, {row.ciHigh.toFixed(3)}], p ≈ {row.p.toFixed(3)}
              </div>
            ))}
          </div>
        </Glass>
      )}

      {matrices.map((mx) => (
        <Glass key={mx.name} className="mx-2 overflow-x-auto p-3">
          <div className="mb-2 text-[10px] uppercase tracking-wide text-text-2">
            {mx.title}
            {mx.macroLift !== null && (
              <span className="ml-2 normal-case text-text-1">
                macro lift{" "}
                <span
                  className="mono"
                  style={{ color: mx.macroLift >= 1 ? UI_HUES.teal : UI_HUES.amber }}
                >
                  {mx.macroLift.toFixed(2)}×
                </span>
              </span>
            )}
          </div>
          <table className="mono w-full text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wide text-text-2">
                <th className="pr-3">held-out</th>
                <th className="pr-3">val</th>
                <th className="pr-3">n</th>
                <th className="pr-3">prev</th>
                <th className="pr-3">AUC-PR (±std)</th>
                <th>lift</th>
              </tr>
            </thead>
            <tbody>
              {mx.folds.map((f) => (
                <tr key={f.group} className="text-text-1">
                  <td className="pr-3 text-text-0">{f.group}</td>
                  <td className="pr-3">{f.val}</td>
                  <td className="pr-3">{f.n}</td>
                  <td className="pr-3">{f.prevalence.toFixed(3)}</td>
                  <td className="pr-3">
                    {f.mean.toFixed(4)} ± {f.std.toFixed(4)}
                  </td>
                  <td style={{ color: f.lift >= 1 ? UI_HUES.teal : UI_HUES.amber }}>
                    {f.lift.toFixed(2)}×
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Glass>
      ))}

      <div className="grid gap-3 px-2 xl:grid-cols-2">
        {noise.length > 0 && (
          <ChartCard
            title="Label-noise robustness"
            subtitle="test AUC-PR vs % of train labels flipped (mean over seeds; evaluation labels untouched)"
            hue={UI_HUES.amber}
            filename={`${dataset}_label_noise`}
          >
            <AtKChart points={noise} color={CHART_SERIES[2]} label="AUC-PR @ noise%" />
          </ChartCard>
        )}
        {efficiency && efficiency.source.length > 0 && (
          <ChartCard
            title="Cross-domain label efficiency"
            subtitle={
              "frozen-source-encoder probe AUC-PR at k target labels" +
              (efficiency.reference
                ? ` · full-pool ref ${efficiency.reference.source.toFixed(3)} (transfer) vs ${efficiency.reference.raw.toFixed(3)} (no-transfer)`
                : "")
            }
            hue={UI_HUES.violet}
            filename={`${dataset}_label_efficiency`}
          >
            <>
              <AtKChart points={efficiency.source} color={CHART_SERIES[1]} label="AUC-PR @ k" />
              {efficiency.gain.length > 0 && (
                <div className="mono mt-1 text-[10px] text-text-2">
                  gain vs no-transfer:{" "}
                  {efficiency.gain
                    .map(
                      (g) => `k${g.k} ${g.value >= 0 ? "+" : ""}${g.value.toFixed(3)}`,
                    )
                    .join(" · ")}
                </div>
              )}
            </>
          </ChartCard>
        )}
      </div>

      {sensitivity && (
        <Glass className="mx-2 p-3">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-text-2">
            Protocol sensitivity ({sensitivity.nGrid} grid points)
          </div>
          <p className="text-xs text-text-1">
            NMS threshold sweep keeps{" "}
            <span className="mono text-text-0">
              {sensitivity.keptValues.join(" / ")}
            </span>{" "}
            alerts at every threshold
            {sensitivity.keptValues.length === 1 ? " — dedup never fires on Leiden partitions" : ""}
            ; hit totals span{" "}
            <span className="mono text-text-0">
              {sensitivity.hitsMin}–{sensitivity.hitsMax}
            </span>{" "}
            across hit-rule variants (≥1-member → 25% illicit share).
          </p>
        </Glass>
      )}
    </motion.div>
  );
}
