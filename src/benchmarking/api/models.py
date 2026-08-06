"""Versioned read-only benchmark API contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


class Capability(ApiModel):
    name: str
    status: CapabilityState
    freshness: str | None = None
    release_status: str
    source_version: str
    artifact_count: int = Field(default=0, ge=0)


class CapabilityResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    source_version: str
    capabilities: list[Capability]


class ExperimentSummary(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    experiment_id: str
    pattern: str
    dataset_name: str
    dataset_version: str
    git_commit: str
    corpus_fingerprint: str | None = None
    index_fingerprint: str | None = None
    model_deployment: str | None = None
    created_at: str
    count: int = Field(ge=0)
    success_rate: float
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    quality: float | None = None
    security_pass_rate: float | None = None
    estimated_variable_cost: float | None = None
    sample_warning: str | None = None
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


class BenchmarkApiContract(ApiModel):
    """Schema-only wrapper used to generate frontend transport types."""

    capabilities: CapabilityResponse
    experiments: ExperimentListResponse
    comparison: ComparisonResponse
    pattern_summary: PatternSummaryResponse
    native_link: NativeLinkResponse
