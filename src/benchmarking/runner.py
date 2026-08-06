"""Controlled benchmark runner independent of production routing."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.benchmarking.adapters.base import BenchmarkAdapter
from src.benchmarking.evaluation import retrieval_metrics
from src.benchmarking.models import (
    AvailabilityReason,
    BenchmarkCase,
    CaseResult,
    CostEstimate,
    ExperimentManifest,
    MetricValue,
)
from src.observability import benchmark_correlation_context


def _unavailable(unit: str, reason: AvailabilityReason) -> MetricValue:
    return MetricValue(
        unit=unit,
        measurement_type="unavailable",
        unavailable_reason=reason,
    )


class BenchmarkRunner:
    def __init__(self, manifest: ExperimentManifest, adapter: BenchmarkAdapter) -> None:
        self._manifest = manifest
        self._adapter = adapter

    async def run(self, cases: list[BenchmarkCase]) -> list[CaseResult]:
        results: list[CaseResult] = []
        run_id = str(uuid4())
        for case in cases:
            started_at = datetime.now(timezone.utc)
            configuration_id = (
                f"{self._manifest.pattern}:{self._manifest.retrieval_mode}:"
                f"top{self._manifest.top}"
            )
            try:
                with benchmark_correlation_context(
                    {
                        "experiment.id": self._manifest.experiment_id,
                        "pattern": self._manifest.pattern,
                        "configuration.id": configuration_id,
                        "run.id": run_id,
                        "case.id": case.case_id,
                    }
                ):
                    invocation = await self._adapter.invoke(
                        case.query, self._manifest.top
                    )
            except Exception as exc:
                elapsed_ms = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
                from src.benchmarking.adapters.base import InvocationResult

                invocation = InvocationResult(
                    status="error",
                    error_classification=type(exc).__name__,
                    metrics={
                        "client_wall_time_ms": MetricValue(
                            value=elapsed_ms,
                            unit="ms",
                            measurement_type="measured",
                        )
                    },
                )
            ended_at = datetime.now(timezone.utc)
            ranked_source_ids = [reference.source_id for reference in invocation.references]
            ranked_metrics = retrieval_metrics(ranked_source_ids, case.expected_source_ids)
            expected_source_ids = set(case.expected_source_ids)
            if expected_source_ids:
                returned_at_k = set(ranked_source_ids[: self._manifest.top])
                ranked_metrics["recall_at_k"] = (
                    len(expected_source_ids.intersection(returned_at_k))
                    / len(expected_source_ids)
                )
            metrics = invocation.metrics
            not_applicable = AvailabilityReason.NOT_APPLICABLE
            not_exposed = AvailabilityReason.NOT_EXPOSED
            results.append(
                CaseResult(
                    experiment_id=self._manifest.experiment_id,
                    run_id=run_id,
                    case_id=case.case_id,
                    configuration_id=configuration_id,
                    pattern=self._adapter.pattern,
                    query_category=case.category,
                    expected_behavior=case.expected_behavior,
                    started_at=started_at,
                    ended_at=ended_at,
                    status=invocation.status,
                    error_classification=invocation.error_classification,
                    client_wall_time_ms=metrics["client_wall_time_ms"],
                    service_elapsed_time_ms=metrics.get(
                        "service_elapsed_time_ms", _unavailable("ms", not_exposed)
                    ),
                    ttft_ms=metrics.get("ttft_ms", _unavailable("ms", not_applicable)),
                    ttlt_ms=metrics.get("ttlt_ms", _unavailable("ms", not_applicable)),
                    stream_duration_ms=metrics.get(
                        "stream_duration_ms", _unavailable("ms", not_applicable)
                    ),
                    input_tokens=metrics.get(
                        "input_tokens", _unavailable("tokens", not_exposed)
                    ),
                    output_tokens=metrics.get(
                        "output_tokens", _unavailable("tokens", not_exposed)
                    ),
                    reasoning_tokens=metrics.get(
                        "reasoning_tokens", _unavailable("tokens", not_exposed)
                    ),
                    evaluator_tokens=metrics.get(
                        "evaluator_tokens", _unavailable("tokens", not_applicable)
                    ),
                    tokens_per_second=metrics.get(
                        "tokens_per_second", _unavailable("tokens/second", not_applicable)
                    ),
                    retry_count=invocation.retry_count,
                    throttled=invocation.throttled,
                    service_status=invocation.service_status,
                    references=invocation.references,
                    activity=invocation.activity,
                    stage_timings=invocation.stage_timings,
                    local_metrics={
                        **invocation.local_metrics,
                        **ranked_metrics,
                    },
                    estimated_variable_cost=CostEstimate(
                        measurement_type="unavailable",
                        unavailable_reason=AvailabilityReason.UNKNOWN,
                    ),
                    trace_id=invocation.trace_id,
                    response_id=invocation.response_id,
                    conversation_id=invocation.conversation_id,
                )
            )
        return results