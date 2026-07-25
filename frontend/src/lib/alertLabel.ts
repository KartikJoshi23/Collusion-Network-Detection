// Alert ids are machine keys of the form  <dataset>:<model_run_id>:<n>
// e.g.  elliptic_pp_actor:rgcn_actor_s0:5
//
// Shown raw they are unreadable to a reviewer, and they were the single most
// confusing thing on the Case Detail screen ("what is rgcn_actor_s0?").
// This decodes one into plain words. The raw id is never thrown away — it stays
// available as a subtitle / copy target, because it is what the API, the
// exported JSON and the Copilot all key on.

/** Human name for each dataset. */
const DATASET_LABEL: Record<string, string> = {
  elliptic_pp: "Bitcoin payments",
  elliptic_pp_actor: "Bitcoin wallets",
  mendeley_eu: "EU public contracts",
  garcia_rodriguez: "International auctions",
};

/** Human name for the scorer behind a model_run_id. Matched by fragment so a
 *  new seed or suffix does not silently fall through to the raw string. */
const SCORER_RULES: [RegExp, string][] = [
  [/^ens_cal/, "combined model (several models merged)"],
  [/^ens/, "combined model"],
  [/gatv2/, "GATv2 attention network"],
  [/rgcn/, "R-GCN relation network"],
  [/sage/, "GraphSAGE network"],
  [/xgb/, "XGBoost trees"],
];

export interface AlertLabel {
  /** e.g. "Case 5" */
  caseName: string;
  /** e.g. "Bitcoin wallets" */
  dataset: string;
  /** e.g. "R-GCN relation network" */
  scorer: string;
  /** e.g. "attempt 0" — the random seed, when the id carries one */
  attempt?: string;
  /** the original machine key, unchanged */
  raw: string;
  /** one-line human sentence */
  sentence: string;
}

export function decodeAlertId(alertId: string): AlertLabel {
  const parts = alertId.split(":");
  const [ds, runId, n] = [parts[0] ?? "", parts[1] ?? "", parts[2] ?? ""];

  const dataset = DATASET_LABEL[ds] ?? ds;
  const scorer =
    SCORER_RULES.find(([re]) => re.test(runId))?.[1] ?? (runId || "unknown model");
  const seedMatch = /_s(\d+)$/.exec(runId);
  const attempt = seedMatch ? `attempt ${seedMatch[1]}` : undefined;
  const caseName = n ? `Case ${n}` : "Case";

  const sentence = [
    `${caseName} — a group of entities flagged in the ${dataset} dataset`,
    `scored by the ${scorer}${attempt ? ` (${attempt})` : ""}`,
  ].join(", ");

  return { caseName, dataset, scorer, attempt, raw: alertId, sentence };
}
