"""Deterministic aggregation for controlled benchmark results."""

from __future__ import annotations

from statistics import fmean, pstdev

from src.benchmarking.models import (
    ActivityTypeSummary,
    AggregateReport,
    CaseResult,
    LatencySummary,
)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _latency_summary(values: list[float]) -> LatencySummary | None:
    if not values:
        return None
    return LatencySummary(
        count=len(values),
        minimum_ms=min(values),
        maximum_ms=max(values),
        mean_ms=fmean(values),
        standard_deviation_ms=pstdev(values),
        p50_ms=_percentile(values, 0.50),
        p95_ms=_percentile(values, 0.95),
        p99_ms=_percentile(values, 0.99),
    )


def aggregate_results(results: list[CaseResult]) -> AggregateReport:
    if not results:
        raise ValueError("At least one case result is required")

    successful = [result for result in results if result.status in {"success", "partial"}]
    latencies = [
        float(result.client_wall_time_ms.value)
        for result in successful
        if result.client_wall_time_ms.value is not None
    ]
    latency = _latency_summary(latencies)
    cold = _latency_summary([
        float(result.client_wall_time_ms.value)
        for result in successful
        if result.temperature == "cold" and result.client_wall_time_ms.value is not None
    ])
    warm = _latency_summary([
        float(result.client_wall_time_ms.value)
        for result in successful
        if result.temperature == "warm" and result.client_wall_time_ms.value is not None
    ])
    categories = sorted({result.query_category for result in results})
    by_category = {
        category: summary
        for category in categories
        if (summary := _latency_summary([
            float(result.client_wall_time_ms.value)
            for result in successful
            if result.query_category == category
            and result.client_wall_time_ms.value is not None
        ])) is not None
    }
    stage_names = sorted({stage.name for result in successful for stage in result.stage_timings})
    by_stage = {
        name: summary
        for name in stage_names
        if (summary := _latency_summary([
            float(stage.duration_ms.value)
            for result in successful
            for stage in result.stage_timings
            if stage.name == name and stage.duration_ms.value is not None
        ])) is not None
    }
    activity_types = sorted({record.type for result in successful for record in result.activity})
    by_activity_type = {}
    for activity_type in activity_types:
        records = [
            record
            for result in successful
            for record in result.activity
            if record.type == activity_type
        ]
        by_activity_type[activity_type] = ActivityTypeSummary(
            record_count=len(records),
            elapsed_ms=_latency_summary([
                float(record.elapsed_ms)
                for record in records
                if record.elapsed_ms is not None
            ]),
            input_tokens=sum(record.input_tokens or 0 for record in records),
            output_tokens=sum(record.output_tokens or 0 for record in records),
            reasoning_tokens=sum(record.reasoning_tokens or 0 for record in records),
        )

    count = len(results)
    successes = sum(result.status == "success" for result in results)
    errors = sum(result.status in {"error", "timeout"} for result in results)
    throttles = sum(result.throttled for result in results)
    return AggregateReport(
        experiment_id=results[0].experiment_id,
        count=count,
        success_rate=successes / count,
        error_rate=errors / count,
        throttle_rate=throttles / count,
        client_wall_time=latency,
        cold_client_wall_time=cold,
        warm_client_wall_time=warm,
        by_category=by_category,
        by_stage=by_stage,
        by_activity_type=by_activity_type,
        sample_warning=(
            f"Only {count} measured samples; percentile estimates are unstable."
            if count < 30
            else None
        ),
    )