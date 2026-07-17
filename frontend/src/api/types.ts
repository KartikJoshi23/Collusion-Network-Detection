// Response shapes from backend/api/app.py. Hand-authored to mirror the
// endpoints; when the API grows, regenerate from /openapi.json with
// openapi-typescript (§5.4). Every response carries the screening caveat.

export type Domain = "financial" | "procurement";

export interface DatasetSummary {
  dataset: string;
  domain: Domain;
  has_alerts: boolean;
  has_explanations: boolean;
  n_metrics_files: number;
}

export interface DatasetsResponse {
  datasets: DatasetSummary[];
  caveat: string;
}

export interface DomainsResponse {
  domains: Record<string, string[]>;
  caveat: string;
}

export interface AlertRow {
  alert_id: string;
  rank: number;
  risk_score: number;
  n_members: number;
  motif_type: string | null;
  time_window_start: number | null;
  time_window_end: number | null;
  community_id: string | null;
}

export interface AlertsResponse {
  dataset: string;
  budget: number;
  k_effective: number;
  alerts: AlertRow[];
  caveat: string;
}

export interface SubgraphNode {
  node_id: string;
  node_type: string;
  time_first_seen: number | null;
  is_member: boolean;
}

export interface SubgraphEdge {
  src: string;
  dst: string;
  edge_type: string;
  timestamp: number | null;
  amount: number | null;
}

export interface SubgraphResponse {
  alert_id: string;
  hops: number;
  truncated: boolean;
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
  caveat: string;
}

export interface ExplanationResponse {
  bundle: Record<string, unknown>;
  caveat: string;
}

export interface MetricsRun {
  source: string;
  metrics: Record<string, unknown>;
}

export interface MetricsResponse {
  dataset: string;
  runs: MetricsRun[];
  caveat: string;
}

export const SCREENING_CAVEAT =
  "screening signal only — no determination of guilt";
