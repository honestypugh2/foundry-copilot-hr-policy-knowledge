import type {
  ComparisonResponse as ComparisonTransport,
  ExperimentListResponse,
  ExperimentSummary as ExperimentTransport,
  NativeLinkResponse,
  PatternSummaryResponse as PatternSummaryTransport,
} from "../generated/benchmark-api";

const BASE_URL = "/api/benchmarking";

export interface ExperimentSummary {
  schema_version: "1.0";
  experiment_id: string;
  pattern: string;
  dataset_name: string;
  dataset_version: string;
  git_commit: string;
  corpus_fingerprint: string | null;
  index_fingerprint: string | null;
  model_deployment: string | null;
  created_at: string;
  count: number;
  success_rate: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  latency_p99_ms: number | null;
  quality: number | null;
  security_pass_rate: number | null;
  estimated_variable_cost: number | null;
  sample_warning: string | null;
  provenance: Record<string, unknown>;
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
    provenance: item.provenance ?? {},
  };
}

export interface ExperimentProvider {
  experiments(): Promise<{ schema_version: "1.0"; items: ExperimentSummary[] }>;
  compare(baseline: string, candidate: string): Promise<ComparisonResponse>;
  pattern(pattern: string): Promise<PatternSummaryResponse>;
  nativeLink(resourceType: string, sourceId: string): Promise<NativeLinkResponse>;
}

export const benchmarkApi: ExperimentProvider = {
  async experiments() {
    const response = await getJson<ExperimentListResponse>("/experiments");
    return {
      schema_version: response.schema_version ?? "1.0",
      items: response.items.map(normalizeExperiment),
    };
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