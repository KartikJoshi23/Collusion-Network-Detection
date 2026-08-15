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

  // The ensemble's "supervised" member IS the standalone GATv2 run, so the two
  // tiles used to render identical numbers side by side and read like a bug.
  // Fold duplicates into one row and name the alias.
  const seedRows: (SeedAggregate & { alias?: string })[] = [];
  for (const agg of [
    ...seedAggs,
    ...ensembleAggs.map((m) => ({ ...m, label: `ensemble: ${m.label}` })),
  ]) {
    const dup = seedRows.find(
      (r) => r.mean.toFixed(6) === agg.mean.toFixed(6) && r.std.toFixed(6) === agg.std.toFixed(6),
    );
    if (dup) {
      if (!dup.alias) dup.alias = agg.label;
    } else {
      seedRows.push({ ...agg });
    }
  }

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
          How much can you <span className="text-grad">trust these numbers?</span>
        </h3>
        <p className="text-xs text-text-2">
          Each model was built five times with different starting randomness. A
          small spread means the result is stable; a large one means a single run
          would have flattered us. Every value below is copied from a stored
          result — nothing is computed in the browser.
        </p>
      </div>

      {seedRows.length > 0 && (
        <div className="mx-2 overflow-x-auto rounded-md"
          style={{ background: "var(--bg-2)", boxShadow: "inset 0 0 0 1px var(--hairline)" }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-text-2">
                <th className="px-3 py-1.5 text-left font-normal">
                  model / arm (5 attempts)
                </th>
                <th className="px-3 py-1.5 text-right font-normal">
                  average AUC-PR
                </th>
                <th className="px-3 py-1.5 text-right font-normal">
                  spread (±)
                </th>
                <th className="px-3 py-1.5 text-right font-normal">
                  worst … best
                </th>
              </tr>
            </thead>
            <tbody>
              {seedRows.map((agg) => (
                <tr key={agg.label} className="hover-row">
                  <td className="px-3 py-1.5 text-text-1">
                    {agg.label}
                    {agg.alias && (
                      <span className="ml-1.5 text-[10px] text-text-2">
                        (same run as {agg.alias})
                      </span>
                    )}
                  </td>
                  <td className="mono px-3 py-1.5 text-right" style={{ color: UI_HUES.cyan }}>
                    {agg.mean.toFixed(4)}
                  </td>
                  <td className="mono px-3 py-1.5 text-right text-text-2">
                    {agg.std.toFixed(4)}
                  </td>
                  <td className="mono px-3 py-1.5 text-right text-text-2">
                    {agg.perSeed.length
                      ? `${Math.min(...agg.perSeed).toFixed(3)} … ${Math.max(...agg.perSeed).toFixed(3)}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {significance.length > 0 && (
        <Glass className="mx-2 p-3">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-text-2">
            Is the difference real, or luck?
          </div>
          <div className="grid gap-1">
            {significance.map((row) => {
              const wins = row.delta >= 0;
              return (
                <div key={row.name} className="text-xs leading-snug text-text-1">
                  <span className="text-text-0">{row.labelA}</span>{" "}
                  <span style={{ color: wins ? UI_HUES.teal : UI_HUES.amber }}>
                    scores {Math.abs(row.delta).toFixed(3)} {wins ? "HIGHER" : "LOWER"}
                  </span>{" "}
                  than <span className="text-text-0">{row.labelB}</span>.{" "}
                  <span className="text-text-2">
                    Re-testing on 2,000 reshuffles put the gap between{" "}
                    <span className="mono">{row.ciLow.toFixed(3)}</span> and{" "}
                    <span className="mono">{row.ciHigh.toFixed(3)}</span>, so it is
                    a real difference, not luck (p ≈ {row.p.toFixed(3)}).
                  </span>
                </div>
              );
            })}
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
            subtitle="we deliberately corrupted some training answers and re-scored. The test answers were never touched"
            hue={UI_HUES.amber}
            filename={`${dataset}_label_noise`}
            howToRead={
              <>
                <b>Left to right is how many of the training answers we deliberately
                flipped to the wrong value.</b> Up is how well the model still scored
                afterwards. The answers it was <i>tested</i> against were never
                touched — only the ones it learned from.
                <br />
                <br />
                <b>Why do this at all?</b> Real label data is always partly wrong.
                If a small amount of bad answers destroyed the model, it would be
                useless in practice. A line that stays roughly flat is the result you
                want here.
              </>
            }
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
            howToRead={
              <>
                <b>The question here is: does knowing one crime help you learn the
                other one faster?</b> Left to right is how many labelled examples the
                model was given in the new domain. Up is how well it did.
                <br />
                <br />
                We take a model trained on one side, freeze what it learned, and let
                it try the other side with only a handful of answers. The
                &ldquo;gain&rdquo; line underneath compares that against learning the
                new side from scratch.
                <br />
                <br />
                <b>Our honest result:</b> below about five hundred labelled examples,
                transferring never helped in either direction. That is a clean
                negative answer to a question nobody had tested, and we publish it
                rather than bury it.
              </>
            }
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
