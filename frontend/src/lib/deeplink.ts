// Deep-link resolution (§5.4): alert ids are `<dataset>:<model_run>:<rank>`
// (§4.2 alert schema), so a deep-linked alert names its own dataset — and via
// the /datasets index, its domain. Without this, /?view=case&alert=<mendeley…>
// resolves under the financial default and 404s the bundle.
export interface DatasetEntry {
  dataset: string;
  domain: string;
}

export function deepLinkTarget(
  alertId: string | undefined,
  datasets: readonly DatasetEntry[] | undefined,
): DatasetEntry | null {
  if (!alertId || !datasets) return null;
  const prefix = alertId.split(":")[0];
  return datasets.find((d) => d.dataset === prefix) ?? null;
}
