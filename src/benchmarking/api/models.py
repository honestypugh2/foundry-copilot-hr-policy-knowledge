"""Versioned read-only benchmark API contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.benchmarking.decision import SloThresholds


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CapabilityState = Literal[
    "available",
    "unavailable",
    "not_configured",
    "not_authorized",
    "not_applicable",
    "degraded",
]
CapabilityClassification = Literal["reuse", "adapter", "new_gap_coverage"]
ImplementationState = Literal["implemented", "partial", "external_reference"]


class Capability(ApiModel):
    capability_id: str
    name: str
    classification: CapabilityClassification
    status: CapabilityState
    implementation_status: ImplementationState
    freshness: str | None = None
    release_status: str
    source_version: str
    authoritative_system: str
    component: str | None = None
    configuration_source: str | None = None
    limitations: list[str] = Field(default_factory=list)
    deep_link_type: str | None = None
    artifact_count: int = Field(default=0, ge=0)


class CapabilityResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    source_version: str
    capabilities: list[Capability]


class ExperimentSummary(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    experiment_id: str
    pattern: str
    retrieval_mode: str
    dataset_name: str
    dataset_version: str
    git_commit: str
    corpus_fingerprint: str | None = None
    index_fingerprint: str | None = None
    model_deployment: str | None = None
    answer_model: str | None = None
    created_at: str
    count: int = Field(ge=0)
    success_rate: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    quality: float | None = None
    security_pass_rate: float | None = None
    estimated_variable_cost: float | None = None
    sample_warning: str | None = None
    comparison_scope: str
    provenance: dict[str, Any] = Field(default_factory=dict)


class ExperimentListResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    items: list[ExperimentSummary]


class Delta(ApiModel):
    absolute: float | None = None
    relative: float | None = None


class ComparisonResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    baseline: ExperimentSummary
    candidate: ExperimentSummary
    compatible_scope: bool
    incompatibility_reasons: list[str] = Field(default_factory=list)
    deltas: dict[str, Delta]


class PatternEvidence(ApiModel):
    pattern: Literal["A", "A2", "B", "C", "Hosted"]
    automation_boundary: str
    telemetry_boundary: str
    implementation_status: Literal["implemented", "partial"]
    evidence_status: Literal["measured", "fixture_only", "run_required"]
    experiment_count: int = Field(ge=0)
    latest: ExperimentSummary | None = None


class PatternSummaryResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    item: PatternEvidence


class NativeLinkResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    resource_type: str
    source_id: str
    status: CapabilityState
    authoritative_url: str | None = None
    release_status: str


class DecisionScope(ApiModel):
    scope_id: str
    experiment_ids: list[str]


class DecisionEvidence(ApiModel):
    experiment_id: str
    pattern: str
    qualified: bool
    qualification_failures: list[str] = Field(default_factory=list)
    on_pareto_frontier: bool
    publication_ready: bool
    publication_blockers: list[str] = Field(default_factory=list)


class DecisionResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    goal: Literal["quality", "balanced", "speed"]
    thresholds: SloThresholds
    selected_scope: str | None = None
    available_scopes: list[DecisionScope] = Field(default_factory=list)
    evidence: list[DecisionEvidence] = Field(default_factory=list)
    frontier_experiment_ids: list[str] = Field(default_factory=list)
    recommended_experiment_id: str | None = None
    leading_experiment_id: str | None = None
    leading_reason: str | None = None
    selection_method: str
    blockers: list[str] = Field(default_factory=list)


class BenchmarkApiContract(ApiModel):
    """Schema-only wrapper used to generate frontend transport types."""

    capabilities: CapabilityResponse
    experiments: ExperimentListResponse
    comparison: ComparisonResponse
    pattern_summary: PatternSummaryResponse
    native_link: NativeLinkResponse
    decision: DecisionResponse
