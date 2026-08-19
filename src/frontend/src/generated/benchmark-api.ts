/* Generated from the backend Pydantic schema. Do not edit. */

export type ArtifactCount = number;
export type AuthoritativeSystem = string;
export type CapabilityId = string;
export type Classification = "reuse" | "adapter" | "new_gap_coverage";
export type Component = string | null;
export type ConfigurationSource = string | null;
export type DeepLinkType = string | null;
export type Freshness = string | null;
export type ImplementationStatus = "implemented" | "partial" | "external_reference";
export type Limitations = string[];
export type Name = string;
export type ReleaseStatus = string;
export type SourceVersion = string;
export type Status = "available" | "unavailable" | "not_configured" | "not_authorized" | "not_applicable" | "degraded";
export type Capabilities = Capability[];
export type SchemaVersion = "1.0";
export type SourceVersion1 = string;
export type AnswerModel = string | null;
export type ComparisonScope = string;
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
export type RetrievalMode = string;
export type SampleWarning = string | null;
export type SchemaVersion1 = "1.0";
export type SecurityPassRate = number | null;
export type SuccessRate = number | null;
export type CompatibleScope = boolean;
export type Absolute = number | null;
export type Caveat = string | null;
export type Comparable = boolean;
export type Relative = number | null;
export type IncompatibilityReasons = string[];
export type SchemaVersion2 = "1.0";
export type ExperimentIds = string[];
export type ScopeId = string;
export type AvailableScopes = DecisionScope[];
export type Blockers = string[];
export type ExperimentId1 = string;
export type OnParetoFrontier = boolean;
export type Pattern1 = string;
export type PublicationBlockers = string[];
export type PublicationReady = boolean;
export type QualificationFailures = string[];
export type Qualified = boolean;
export type Evidence = DecisionEvidence[];
export type FrontierExperimentIds = string[];
export type Goal = "quality" | "balanced" | "speed";
export type LeadingExperimentId = string | null;
export type LeadingReason = string | null;
export type RecommendedExperimentId = string | null;
export type SchemaVersion3 = "1.0";
export type SelectedScope = string | null;
export type SelectionMethod = string;
export type MaximumEstimatedVariableCost = number;
export type MaximumLatencyP95Ms = number;
export type MinimumQuality = number;
export type MinimumSecurityPassRate = number;
export type MinimumSuccessRate = number;
export type Items = ExperimentSummary[];
export type SchemaVersion4 = "1.0";
export type AuthoritativeUrl = string | null;
export type ReleaseStatus1 = string;
export type ResourceType = string;
export type SchemaVersion5 = "1.0";
export type SourceId = string;
export type Status1 = "available" | "unavailable" | "not_configured" | "not_authorized" | "not_applicable" | "degraded";
export type AutomationBoundary = string;
export type EvidenceStatus = "measured" | "fixture_only" | "run_required";
export type ExperimentCount = number;
export type ImplementationStatus1 = "implemented" | "partial";
export type Pattern2 = "A" | "A2" | "B" | "C" | "Hosted";
export type TelemetryBoundary = string;
export type SchemaVersion6 = "1.0";

/**
 * Schema-only wrapper used to generate frontend transport types.
 */
export interface BenchmarkApiContract {
  capabilities: CapabilityResponse;
  comparison: ComparisonResponse;
  decision: DecisionResponse;
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
  authoritative_system: AuthoritativeSystem;
  capability_id: CapabilityId;
  classification: Classification;
  component?: Component;
  configuration_source?: ConfigurationSource;
  deep_link_type?: DeepLinkType;
  freshness?: Freshness;
  implementation_status: ImplementationStatus;
  limitations?: Limitations;
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
  answer_model?: AnswerModel;
  comparison_scope: ComparisonScope;
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
  retrieval_mode: RetrievalMode;
  sample_warning?: SampleWarning;
  schema_version?: SchemaVersion1;
  security_pass_rate?: SecurityPassRate;
  success_rate?: SuccessRate;
}
export interface Provenance {
  [k: string]: unknown;
}
export interface Deltas {
  [k: string]: Delta;
}
export interface Delta {
  absolute?: Absolute;
  caveat?: Caveat;
  comparable?: Comparable;
  relative?: Relative;
}
export interface DecisionResponse {
  available_scopes?: AvailableScopes;
  blockers?: Blockers;
  evidence?: Evidence;
  frontier_experiment_ids?: FrontierExperimentIds;
  goal: Goal;
  leading_experiment_id?: LeadingExperimentId;
  leading_reason?: LeadingReason;
  recommended_experiment_id?: RecommendedExperimentId;
  schema_version?: SchemaVersion3;
  selected_scope?: SelectedScope;
  selection_method: SelectionMethod;
  thresholds: SloThresholds;
}
export interface DecisionScope {
  experiment_ids: ExperimentIds;
  scope_id: ScopeId;
}
export interface DecisionEvidence {
  experiment_id: ExperimentId1;
  on_pareto_frontier: OnParetoFrontier;
  pattern: Pattern1;
  publication_blockers?: PublicationBlockers;
  publication_ready: PublicationReady;
  qualification_failures?: QualificationFailures;
  qualified: Qualified;
}
export interface SloThresholds {
  maximum_estimated_variable_cost: MaximumEstimatedVariableCost;
  maximum_latency_p95_ms: MaximumLatencyP95Ms;
  minimum_quality: MinimumQuality;
  minimum_security_pass_rate: MinimumSecurityPassRate;
  minimum_success_rate: MinimumSuccessRate;
}
export interface ExperimentListResponse {
  items: Items;
  schema_version?: SchemaVersion4;
}
export interface NativeLinkResponse {
  authoritative_url?: AuthoritativeUrl;
  release_status: ReleaseStatus1;
  resource_type: ResourceType;
  schema_version?: SchemaVersion5;
  source_id: SourceId;
  status: Status1;
}
export interface PatternSummaryResponse {
  item: PatternEvidence;
  schema_version?: SchemaVersion6;
}
export interface PatternEvidence {
  automation_boundary: AutomationBoundary;
  evidence_status: EvidenceStatus;
  experiment_count: ExperimentCount;
  implementation_status: ImplementationStatus1;
  latest?: ExperimentSummary | null;
  pattern: Pattern2;
  telemetry_boundary: TelemetryBoundary;
}
