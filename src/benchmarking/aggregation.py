"""Deterministic aggregation for controlled benchmark results."""

from __future__ import annotations

from math import sqrt
from statistics import fmean, pstdev

from src.benchmarking.models import (
    ActivityTypeSummary,
    AggregateReport,
    AvailabilityReason,
    CaseResult,
    ConfidenceInterval,
    CostEstimate,
    LatencySummary,
    VariableCostSummary,
)


def wilson_score_interval(passed: int, count: int) -> ConfidenceInterval:
    """Return a two-sided 95% Wilson score interval for a binomial proportion."""
    if count < 1:
        raise ValueError("Wilson score intervals require at least one observation")
    if passed < 0 or passed > count:
        raise ValueError("passed must be between zero and count")
    z = 1.959963984540054
    proportion = passed / count
    denominator = 1 + z**2 / count
    center = (proportion + z**2 / (2 * count)) / denominator
    margin = (
        z
        * sqrt(proportion * (1 - proportion) / count + z**2 / (4 * count**2))
        / denominator
    )
    return ConfidenceInterval(lower=max(0, center - margin), upper=min(1, center + margin))


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


def _variable_cost_summary(results: list[CaseResult]) -> VariableCostSummary:
    estimates = [result.estimated_variable_cost for result in results]
    available = [estimate for estimate in estimates if estimate.amount is not None]
    unavailable_reason = next(
        (
            estimate.unavailable_reason
            for estimate in estimates
            if estimate.unavailable_reason is not None
        ),
        AvailabilityReason.UNKNOWN,
    )
    if len(available) != len(estimates):
        unavailable = CostEstimate(
            measurement_type="unavailable",
            unavailable_reason=unavailable_reason,
            assumptions=[
                f"Only {len(available)} of {len(estimates)} invocations had "
                "complete service-reported quantities."
            ],
        )
        return VariableCostSummary(
            invocation_count=len(estimates),
            priced_invocation_count=len(available),
            mean_per_invocation=unavailable,
            run_total=unavailable.model_copy(deep=True),
        )

    currencies = {estimate.currency for estimate in available}
    profiles = {estimate.pricing_profile for estimate in available}
    if len(currencies) != 1 or len(profiles) != 1:
        unavailable = CostEstimate(
            measurement_type="unavailable",
            unavailable_reason=AvailabilityReason.UNKNOWN,
            assumptions=[
                "Variable costs use inconsistent currencies or pricing profiles."
            ],
        )
        return VariableCostSummary(
            invocation_count=len(estimates),
            priced_invocation_count=len(available),
            mean_per_invocation=unavailable,
            run_total=unavailable.model_copy(deep=True),
        )

    total_amount = sum(float(estimate.amount) for estimate in available)
    common = available[0]
    common_fields = {
        "currency": common.currency,
        "measurement_type": "estimated",
        "pricing_profile": common.pricing_profile,
        "assumptions": common.assumptions,
        "excluded_costs": common.excluded_costs,
    }
    return VariableCostSummary(
        invocation_count=len(estimates),
        priced_invocation_count=len(available),
        mean_per_invocation=CostEstimate(
            amount=total_amount / len(estimates),
            formula="sum(per-invocation variable cost) / invocation_count",
            measured_quantities={"invocation_count": float(len(estimates))},
            **common_fields,
        ),
        run_total=CostEstimate(
            amount=total_amount,
            formula="sum(per-invocation variable cost)",
            measured_quantities={"invocation_count": float(len(estimates))},
            **common_fields,
        ),
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
    variable_cost = _variable_cost_summary(results)
    successes = sum(result.status == "success" for result in results)
    partials = sum(result.status == "partial" for result in results)
    error_count = sum(result.status == "error" for result in results)
    timeout_count = sum(result.status == "timeout" for result in results)
    errors = error_count + timeout_count
    throttles = sum(result.throttled for result in results)
    return AggregateReport(
        experiment_id=results[0].experiment_id,
        count=count,
        success_count=successes,
        partial_count=partials,
        error_count=error_count,
        timeout_count=timeout_count,
        throttle_count=throttles,
        success_rate=successes / count,
        error_rate=errors / count,
        throttle_rate=throttles / count,
        rate_confidence_intervals={
            "success_rate": wilson_score_interval(successes, count),
            "error_rate": wilson_score_interval(errors, count),
            "throttle_rate": wilson_score_interval(throttles, count),
        },
        client_wall_time=latency,
        cold_client_wall_time=cold,
        warm_client_wall_time=warm,
        by_category=by_category,
        by_stage=by_stage,
        by_activity_type=by_activity_type,
        variable_cost=variable_cost,
        sample_warning=(
            f"Only {count} measured samples; percentile estimates are unstable."
            if count < 30
            else None
        ),
        provenance={
            "estimated_variable_cost": variable_cost.mean_per_invocation.amount,
            "estimated_variable_cost_currency": variable_cost.mean_per_invocation.currency,
            "estimated_variable_cost_statistic": "mean_per_invocation",
            "estimated_variable_cost_measurement_type": (
                variable_cost.mean_per_invocation.measurement_type
            ),
            "estimated_variable_cost_pricing_profile": (
                variable_cost.mean_per_invocation.pricing_profile
            ),
            "estimated_variable_cost_sample_count": (
                variable_cost.priced_invocation_count
            ),
            "billed_cost_reconciliation": "separate_azure_cost_management",
        },
    )