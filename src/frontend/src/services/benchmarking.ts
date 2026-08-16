import type {
  CapabilityResponse as CapabilityTransport,
  ComparisonResponse as ComparisonTransport,
  DecisionResponse as DecisionTransport,
  ExperimentListResponse,
  ExperimentSummary as ExperimentTransport,
  NativeLinkResponse,
  PatternSummaryResponse as PatternSummaryTransport,
} from "../generated/benchmark-api";

const BASE_URL = "/api/benchmarking";

export interface LatencySummary {
  count: number;
  minimum_ms: number;
  maximum_ms: number;
  mean_ms: number;
  standard_deviation_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}

export interface ConfidenceInterval {
  lower: number;
  upper: number;
  confidence_level: number;
  method: "wilson_score";
}

export interface ProportionSummary {
  passed: number;
  count: number;
  pass_rate: number;
  confidence_interval: ConfidenceInterval;
}

export interface CostEstimate {
  amount: number | null;
  currency: string;
  measurement_type: string;
  pricing_profile: string | null;
  formula: string | null;
  assumptions: string[];
  excluded_costs: string[];
  unavailable_reason: string | null;
}

export interface ExperimentReport {
  manifest: Record<string, unknown> & { experiment_id: string; retrieval_mode: string; dirty_worktree: boolean };
  aggregate: {
    count: number;
    success_count?: number;
    partial_count?: number;
    error_count?: number;
    timeout_count?: number;
    throttle_count?: number;
    success_rate: number | null;
    error_rate: number | null;
    throttle_rate: number;
    rate_confidence_intervals?: Record<string, ConfidenceInterval>;
    client_wall_time: LatencySummary | null;
    cold_client_wall_time: LatencySummary | null;
    warm_client_wall_time: LatencySummary | null;
    by_category: Record<string, LatencySummary>;
    by_stage: Record<string, LatencySummary>;
    by_activity_type: Record<string, { record_count: number; elapsed_ms: LatencySummary | null; input_tokens: number; output_tokens: number; reasoning_tokens: number }>;
    quality_by_category?: Record<string, ProportionSummary>;
    security_by_category?: Record<string, ProportionSummary>;
    variable_cost: { invocation_count: number; priced_invocation_count: number; mean_per_invocation: CostEstimate; run_total: CostEstimate };
    sample_warning: string | null;
    provenance: Record<string, unknown>;
  };
}

export interface Capability {
  capability_id: string;
  name: string;
  classification: "reuse" | "adapter" | "new_gap_coverage";
  status: string;
  implementation_status: "implemented" | "partial" | "external_reference";
  release_status: string;
  authoritative_system: string;
  component: string | null;
  limitations: string[];
  deep_link_type: string | null;
}

export interface ExperimentSummary {
  schema_version: "1.0";
  experiment_id: string;
  pattern: string;
  retrieval_mode: string;
  dataset_name: string;
  dataset_version: string;
  git_commit: string;
  corpus_fingerprint: string | null;
  index_fingerprint: string | null;
  model_deployment: string | null;
  created_at: string;
  count: number;
  success_rate: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  quality: number | null;
  security_pass_rate: number | null;
  estimated_variable_cost: number | null;
  sample_warning: string | null;
  comparison_scope: string;
  provenance: Record<string, unknown>;
}

export interface DecisionResponse {
  schema_version: "1.0";
  goal: "quality" | "balanced" | "speed";
  thresholds: DecisionTransport["thresholds"];
  selected_scope: string | null;
  available_scopes: NonNullable<DecisionTransport["available_scopes"]>;
  evidence: NonNullable<DecisionTransport["evidence"]>;
  frontier_experiment_ids: string[];
  recommended_experiment_id: string | null;
  leading_experiment_id: string | null;
  leading_reason: string | null;
  selection_method: string;
  blockers: string[];
}

export interface ComparisonResponse {
  schema_version: "1.0";
  baseline: ExperimentSummary;
  candidate: ExperimentSummary;
  compatible_scope: boolean;
  incompatibility_reasons: string[];
  deltas: Record<string, { absolute: number | null; relative: number | null }>;
}
export interface PatternSummaryResponse {
  schema_version: "1.0";
  item: {
    pattern: "A" | "A2" | "B" | "C" | "Hosted";
    automation_boundary: string;
    telemetry_boundary: string;
    implementation_status: "implemented" | "partial";
    evidence_status: "measured" | "fixture_only" | "run_required";
    experiment_count: number;
    latest: ExperimentSummary | null;
  };
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) throw new Error(`Benchmark API returned ${response.status}`);
  return response.json() as Promise<T>;
}

function normalizeExperiment(item: ExperimentTransport): ExperimentSummary {
  return {
    schema_version: item.schema_version ?? "1.0",
    experiment_id: item.experiment_id,
    pattern: item.pattern,
    retrieval_mode: item.retrieval_mode,
    dataset_name: item.dataset_name,
    dataset_version: item.dataset_version,
    git_commit: item.git_commit,
    corpus_fingerprint: item.corpus_fingerprint ?? null,
    index_fingerprint: item.index_fingerprint ?? null,
    model_deployment: item.model_deployment ?? null,
    created_at: item.created_at,
    count: item.count,
    success_rate: item.success_rate,
    latency_p50_ms: item.latency_p50_ms ?? null,
    latency_p95_ms: item.latency_p95_ms ?? null,
    latency_p99_ms: item.latency_p99_ms ?? null,
    quality: item.quality ?? null,
    security_pass_rate: item.security_pass_rate ?? null,
    estimated_variable_cost: item.estimated_variable_cost ?? null,
    sample_warning: item.sample_warning ?? null,
    comparison_scope: item.comparison_scope,
    provenance: item.provenance ?? {},
  };
}

export interface ExperimentProvider {
  capabilities(): Promise<{ schema_version: "1.0"; capabilities: Capability[] }>;
  experiments(): Promise<{ schema_version: "1.0"; items: ExperimentSummary[] }>;
  experiment(experimentId: string): Promise<ExperimentReport>;
  compare(baseline: string, candidate: string): Promise<ComparisonResponse>;
  decision(goal: "quality" | "balanced" | "speed", scope?: string): Promise<DecisionResponse>;
  pattern(pattern: string): Promise<PatternSummaryResponse>;
  nativeLink(resourceType: string, sourceId: string): Promise<NativeLinkResponse>;
}

export const benchmarkApi: ExperimentProvider = {
  async capabilities() {
    const response = await getJson<CapabilityTransport>("/capabilities");
    return {
      schema_version: response.schema_version ?? "1.0",
      capabilities: response.capabilities.map((item) => ({
        capability_id: item.capability_id,
        name: item.name,
        classification: item.classification,
        status: item.status,
        implementation_status: item.implementation_status,
        release_status: item.release_status,
        authoritative_system: item.authoritative_system,
        component: item.component ?? null,
        limitations: item.limitations ?? [],
        deep_link_type: item.deep_link_type ?? null,
      })),
    };
  },
  async experiments() {
    const response = await getJson<ExperimentListResponse>("/experiments");
    return {
      schema_version: response.schema_version ?? "1.0",
      items: response.items.map(normalizeExperiment),
    };
  },
  experiment(experimentId: string) {
    return getJson<ExperimentReport>(`/experiments/${encodeURIComponent(experimentId)}`);
  },
  async compare(baseline: string, candidate: string) {
    const response = await getJson<ComparisonTransport>(
      `/comparisons?baseline=${encodeURIComponent(baseline)}&candidate=${encodeURIComponent(candidate)}`
    );
    return {
      schema_version: response.schema_version ?? "1.0",
      baseline: normalizeExperiment(response.baseline),
      candidate: normalizeExperiment(response.candidate),
      compatible_scope: response.compatible_scope,
      incompatibility_reasons: response.incompatibility_reasons ?? [],
      deltas: Object.fromEntries(
        Object.entries(response.deltas).map(([name, delta]) => [
          name,
          { absolute: delta.absolute ?? null, relative: delta.relative ?? null },
        ])
      ),
    };
  },
  async decision(goal, scope) {
    const response = await getJson<DecisionTransport>(
      `/decisions?${new URLSearchParams({ goal, ...(scope ? { scope } : {}) })}`
    );
    return {
      schema_version: response.schema_version ?? "1.0",
      goal: response.goal,
      thresholds: response.thresholds,
      selected_scope: response.selected_scope ?? null,
      available_scopes: response.available_scopes ?? [],
      evidence: response.evidence ?? [],
      frontier_experiment_ids: response.frontier_experiment_ids ?? [],
      recommended_experiment_id: response.recommended_experiment_id ?? null,
      leading_experiment_id: response.leading_experiment_id ?? null,
      leading_reason: response.leading_reason ?? null,
      selection_method: response.selection_method,
      blockers: response.blockers ?? [],
    };
  },
  async pattern(pattern: string) {
    const response = await getJson<PatternSummaryTransport>(
      `/patterns/${encodeURIComponent(pattern)}/summary`
    );
    return {
      schema_version: response.schema_version ?? "1.0",
      item: {
        ...response.item,
        latest: response.item.latest ? normalizeExperiment(response.item.latest) : null,
      },
    };
  },
  nativeLink(resourceType: string, sourceId: string) {
    return getJson<NativeLinkResponse>(
      `/links/${encodeURIComponent(resourceType)}/${encodeURIComponent(sourceId)}`
    );
  },
};