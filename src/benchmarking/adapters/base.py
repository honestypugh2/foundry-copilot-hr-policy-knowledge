"""Shared adapter protocol for repository benchmark paths."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.benchmarking.models import (
    ActivityRecord,
    MetricValue,
    RetrievalReference,
    StageTiming,
)


class InvocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error", "timeout", "partial"] = "success"
    answer: str | None = None
    references: list[RetrievalReference] = Field(default_factory=list)
    activity: list[ActivityRecord] = Field(default_factory=list)
    stage_timings: list[StageTiming] = Field(default_factory=list)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    local_metrics: dict[str, float | bool] = Field(default_factory=dict)
    error_classification: str | None = None
    retry_count: int = 0
    throttled: bool = False
    service_status: str | None = None
    trace_id: str | None = None
    response_id: str | None = None
    conversation_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkAdapter(Protocol):
    @property
    def pattern(self) -> Literal["A", "A2", "B", "C", "Hosted"]: ...

    @property
    def invocation_path(self) -> str: ...

    async def invoke(self, query: str, top: int) -> InvocationResult: ...