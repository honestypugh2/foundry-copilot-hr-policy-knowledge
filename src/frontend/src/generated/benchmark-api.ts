/* Generated from the backend Pydantic schema. Do not edit. */

export type ArtifactCount = number;
export type Freshness = string | null;
export type Name = string;
export type ReleaseStatus = string;
export type SourceVersion = string;
export type Status = "available" | "unavailable" | "not_configured" | "not_authorized" | "not_applicable" | "degraded";
export type Capabilities = Capability[];
export type SchemaVersion = "1.0";
export type SourceVersion1 = string;
export type CorpusFingerprint = string | null;
export type Count = number;
export type CreatedAt = string;
export type DatasetName = string;
export type DatasetVersion = string;
export type EstimatedVariableCost = number | null;
export type ExperimentId = string;
export type GitCommit = string;
export type IndexFingerprint = string | null;
export type LatencyP50Ms = number | null;
export type LatencyP95Ms = number | null;
export type LatencyP99Ms = number | null;
export type ModelDeployment = string | null;
export type Pattern = string;
export type Quality = number | null;
export type SampleWarning = string | null;
export type SchemaVersion1 = "1.0";
export type SecurityPassRate = number | null;
export type SuccessRate = number;
export type CompatibleScope = boolean;
export type Absolute = number | null;
export type Relative = number | null;
export type IncompatibilityReasons = string[];
export type SchemaVersion2 = "1.0";
export type Items = ExperimentSummary[];
export type SchemaVersion3 = "1.0";
export type AuthoritativeUrl = string | null;
export type ReleaseStatus1 = string;
export type ResourceType = string;
export type SchemaVersion4 = "1.0";
export type SourceId = string;
export type Status1 = "available" | "unavailable" | "not_configured" | "not_authorized" | "not_applicable" | "degraded";
export type AutomationBoundary = string;
export type ExperimentCount = number;
export type Pattern1 = "A" | "A2" | "B" | "C" | "Hosted";
export type TelemetryBoundary = string;
export type SchemaVersion5 = "1.0";

/**
 * Schema-only wrapper used to generate frontend transport types.
 */
export interface BenchmarkApiContract {
  capabilities: CapabilityResponse;
  comparison: ComparisonResponse;
  experiments: ExperimentListResponse;
  native_link: NativeLinkResponse;
  pattern_summary: PatternSummaryResponse;
}
export interface CapabilityResponse {
  capabilities: Capabilities;
  schema_version?: SchemaVersion;
  source_version: SourceVersion1;
}
export interface Capability {
  artifact_count?: ArtifactCount;
  freshness?: Freshness;
  name: Name;
  release_status: ReleaseStatus;
  source_version: SourceVersion;
  status: Status;
}
export interface ComparisonResponse {
  baseline: ExperimentSummary;
  candidate: ExperimentSummary;
  compatible_scope: CompatibleScope;
  deltas: Deltas;
  incompatibility_reasons?: IncompatibilityReasons;
  schema_version?: SchemaVersion2;
}
export interface ExperimentSummary {
  corpus_fingerprint?: CorpusFingerprint;
  count: Count;
  created_at: CreatedAt;
  dataset_name: DatasetName;
  dataset_version: DatasetVersion;
  estimated_variable_cost?: EstimatedVariableCost;
  experiment_id: ExperimentId;
  git_commit: GitCommit;
  index_fingerprint?: IndexFingerprint;
  latency_p50_ms?: LatencyP50Ms;
  latency_p95_ms?: LatencyP95Ms;
  latency_p99_ms?: LatencyP99Ms;
  model_deployment?: ModelDeployment;
  pattern: Pattern;
  provenance?: Provenance;
  quality?: Quality;
  sample_warning?: SampleWarning;
  schema_version?: SchemaVersion1;
  security_pass_rate?: SecurityPassRate;
  success_rate: SuccessRate;
}
export interface Provenance {
  [k: string]: unknown;
}
export interface Deltas {
  [k: string]: Delta;
}
export interface Delta {
  absolute?: Absolute;
  relative?: Relative;
}
export interface ExperimentListResponse {
  items: Items;
  schema_version?: SchemaVersion3;
}
export interface NativeLinkResponse {
  authoritative_url?: AuthoritativeUrl;
  release_status: ReleaseStatus1;
  resource_type: ResourceType;
  schema_version?: SchemaVersion4;
  source_id: SourceId;
  status: Status1;
}
export interface PatternSummaryResponse {
  item: PatternEvidence;
  schema_version?: SchemaVersion5;
}
export interface PatternEvidence {
  automation_boundary: AutomationBoundary;
  experiment_count: ExperimentCount;
  latest?: ExperimentSummary | null;
  pattern: Pattern1;
  telemetry_boundary: TelemetryBoundary;
}
