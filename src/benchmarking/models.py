"""Version 1 contracts for controlled HR policy experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AvailabilityReason(StrEnum):
    NOT_EXPOSED = "not_exposed"
    NOT_EXPOSED_BY_MCP = "not_exposed_by_mcp"
    NOT_APPLICABLE = "not_applicable"
    NOT_CONFIGURED = "not_configured"
    NOT_AUTHORIZED = "not_authorized"
    UNKNOWN = "unknown"


class MetricValue(StrictModel):
    value: float | int | None = None
    unit: str
    measurement_type: Literal["measured", "service_reported", "estimated", "unavailable"]
    unavailable_reason: AvailabilityReason | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> "MetricValue":
        if self.value is None and self.unavailable_reason is None:
            raise ValueError("A missing metric requires unavailable_reason")
        if self.value is not None and self.unavailable_reason is not None:
            raise ValueError("An available metric cannot have unavailable_reason")
        return self


class ActivityRecord(BaseModel):
    """Lossless provider activity with normalized fields when known."""

    model_config = ConfigDict(extra="allow")

    type: str
    id: str | int | None = None
    elapsed_ms: float | None = Field(default=None, alias="elapsedMs")
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    reasoning_tokens: int | None = Field(default=None, alias="reasoningTokens")


class StageTiming(StrictModel):
    """One named timing observation from an instrumented invocation boundary."""

    name: str
    duration_ms: MetricValue


class RetrievalReference(StrictModel):
    source_id: str
    policy_number: str | None = None
    title: str | None = None
    score: float | None = None
    source_url: str | None = None


class PricingRate(StrictModel):
    meter: str
    unit: str
    unit_price: float = Field(ge=0)


class PricingProfile(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    name: str
    version: str
    currency: str
    effective_date: str
    pricing_scope: str
    rates: list[PricingRate] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    excluded_costs: list[str] = Field(default_factory=list)


class CostEstimate(StrictModel):
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    measurement_type: Literal["estimated", "unavailable"]
    pricing_profile: str | None = None
    formula: str | None = None
    measured_quantities: dict[str, float] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    excluded_costs: list[str] = Field(default_factory=list)
    unavailable_reason: AvailabilityReason | None = None

    @model_validator(mode="after")
    def validate_estimate(self) -> "CostEstimate":
        if self.amount is None and self.unavailable_reason is None:
            raise ValueError("A missing cost estimate requires unavailable_reason")
        if self.amount is not None:
            if not self.currency or not self.pricing_profile or not self.formula:
                raise ValueError(
                    "An available cost estimate requires currency, pricing_profile, and formula"
                )
            if self.unavailable_reason is not None:
                raise ValueError("An available cost estimate cannot have unavailable_reason")
        return self


class BenchmarkCase(StrictModel):
    case_id: str
    query: str
    category: str
    expected_behavior: str
    expected_source_ids: list[str] = Field(default_factory=list)


class ExperimentManifest(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    experiment_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    git_commit: str
    dirty_worktree: bool
    runner_version: str = "0.1.0"
    dataset_name: str
    dataset_version: str
    corpus_fingerprint: str
    index_fingerprint: str
    pattern: Literal["A", "A2", "B", "C", "Hosted"]
    retrieval_mode: str
    invocation_path: str
    api_version: str | None = None
    output_mode: str
    model_deployment: str | None = None
    model_version: str | None = None
    retrieval_reasoning_effort: Literal["minimal", "low", "medium"] | None = None
    semantic_configuration: str | None = None
    search_sku: str | None = None
    search_replicas: int | None = Field(default=None, ge=1)
    search_partitions: int | None = Field(default=None, ge=1)
    vector_configuration: dict[str, Any] = Field(default_factory=dict)
    output_document_limit: int | None = Field(default=None, ge=1)
    output_token_limit: int | None = Field(default=None, ge=1)
    query_filter: str | None = None
    knowledge_source_settings: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str | None = None
    agent_version: str | None = None
    configuration_version: str | None = None
    region: str | None = None
    client_location: str | None = None
    top: int = Field(default=5, ge=1)
    warmup_count: int = Field(default=0, ge=0)
    measured_repetitions: int = Field(default=1, ge=1)
    concurrency: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=30.0, gt=0)
    random_seed: int = 0
    pricing_profile: str | None = None


class CaseResult(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    experiment_id: str
    run_id: str
    case_id: str
    configuration_id: str
    pattern: Literal["A", "A2", "B", "C", "Hosted"]
    query_category: str
    expected_behavior: str
    temperature: Literal["cold", "warm", "unspecified"] = "unspecified"
    started_at: datetime
    ended_at: datetime
    status: Literal["success", "error", "timeout", "partial"]
    error_classification: str | None = None
    client_wall_time_ms: MetricValue
    service_elapsed_time_ms: MetricValue
    ttft_ms: MetricValue
    ttlt_ms: MetricValue
    stream_duration_ms: MetricValue
    input_tokens: MetricValue
    output_tokens: MetricValue
    reasoning_tokens: MetricValue
    evaluator_tokens: MetricValue
    tokens_per_second: MetricValue
    retry_count: int = Field(default=0, ge=0)
    throttled: bool = False
    service_status: str | None = None
    references: list[RetrievalReference] = Field(default_factory=list)
    activity: list[ActivityRecord] = Field(default_factory=list)
    stage_timings: list[StageTiming] = Field(default_factory=list)
    local_metrics: dict[str, float | bool] = Field(default_factory=dict)
    estimated_variable_cost: CostEstimate
    trace_id: str | None = None
    response_id: str | None = None
    conversation_id: str | None = None
    evaluation_run_id: str | None = None


class LatencySummary(StrictModel):
    count: int
    minimum_ms: float
    maximum_ms: float
    mean_ms: float
    standard_deviation_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class ActivityTypeSummary(StrictModel):
    record_count: int
    elapsed_ms: LatencySummary | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


class AggregateReport(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    experiment_id: str
    count: int
    success_rate: float
    error_rate: float
    throttle_rate: float
    client_wall_time: LatencySummary | None
    cold_client_wall_time: LatencySummary | None = None
    warm_client_wall_time: LatencySummary | None = None
    by_category: dict[str, LatencySummary] = Field(default_factory=dict)
    by_stage: dict[str, LatencySummary] = Field(default_factory=dict)
    by_activity_type: dict[str, ActivityTypeSummary] = Field(default_factory=dict)
    sample_warning: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)