// TanStack Query hooks — caching, loading/error/empty states as first-class UI.
import { useQuery } from "@tanstack/react-query";
import { apiGet, enc } from "./client";
import type {
  AlertsResponse,
  DatasetsResponse,
  ExplanationResponse,
  MetricsResponse,
  RigorResponse,
  SubgraphResponse,
} from "./types";

export function useDatasets() {
  return useQuery({
    queryKey: ["datasets"],
    queryFn: () => apiGet<DatasetsResponse>("/datasets"),
  });
}

export function useAlerts(dataset: string | undefined, budget: number) {
  return useQuery({
    queryKey: ["alerts", dataset, budget],
    queryFn: () =>
      apiGet<AlertsResponse>(`/datasets/${enc(dataset!)}/alerts`, { budget }),
    enabled: !!dataset,
  });
}

export function useSubgraph(
  dataset: string | undefined,
  alertId: string | undefined,
  hops = 1,
  enabled = true,
) {
  return useQuery({
    queryKey: ["subgraph", dataset, alertId, hops],
    queryFn: () =>
      apiGet<SubgraphResponse>(
        `/datasets/${enc(dataset!)}/subgraph/${enc(alertId!)}`,
        { hops },
      ),
    enabled: enabled && !!dataset && !!alertId,
  });
}

export function useExplanation(
  dataset: string | undefined,
  alertId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ["explanation", dataset, alertId],
    queryFn: () =>
      apiGet<ExplanationResponse>(
        `/datasets/${enc(dataset!)}/explanations/${enc(alertId!)}`,
      ),
    enabled: enabled && !!dataset && !!alertId,
    retry: false, // a missing bundle is a normal 404, not a transient error
  });
}

export function useMetrics(dataset: string | undefined) {
  return useQuery({
    queryKey: ["metrics", dataset],
    queryFn: () => apiGet<MetricsResponse>(`/datasets/${enc(dataset!)}/metrics`),
    enabled: !!dataset,
    retry: false,
  });
}

export function useRigor(dataset: string | undefined) {
  return useQuery({
    queryKey: ["rigor", dataset],
    queryFn: () => apiGet<RigorResponse>(`/datasets/${enc(dataset!)}/rigor`),
    enabled: !!dataset,
    retry: false, // absence of rigor artifacts is a normal 404 on thin machines
  });
}
