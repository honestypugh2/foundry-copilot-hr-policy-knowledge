"""Versioned fixed and variable cost estimation from user-supplied rates."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from src.benchmarking.models import (
    AvailabilityReason,
    CostEstimate,
    MetricValue,
    PricingProfile,
)


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed: CostEstimate
    variable: CostEstimate
    total: CostEstimate


def calculate_token_cost(
    profile: PricingProfile,
    metrics: Mapping[str, MetricValue],
) -> CostEstimate:
    """Estimate variable token cost only from service-reported quantities."""
    mapped_rates = [
        rate
        for rate in profile.rates
        if rate.quantity_metric is not None and rate.quantity_per_unit is not None
    ]
    profile_id = f"{profile.name}:{profile.version}"
    if not mapped_rates:
        return CostEstimate(
            currency=profile.currency,
            measurement_type="unavailable",
            pricing_profile=profile_id,
            unavailable_reason=AvailabilityReason.NOT_CONFIGURED,
            assumptions=profile.assumptions,
            excluded_costs=profile.excluded_costs,
        )

    required_metrics: set[str] = set()
    for rate in mapped_rates:
        metric_name = rate.quantity_metric
        if metric_name is None:
            continue
        if metric_name == "uncached_input_tokens":
            required_metrics.update(("input_tokens", "cached_input_tokens"))
        else:
            required_metrics.add(metric_name)
    invalid_metrics = []
    raw_quantities = {}
    for metric_name in required_metrics:
        metric = metrics.get(metric_name)
        if (
            metric is None
            or metric.value is None
            or metric.measurement_type != "service_reported"
            or float(metric.value) < 0
        ):
            invalid_metrics.append(metric_name)
            continue
        raw_quantities[metric_name] = float(metric.value)

    if invalid_metrics:
        return CostEstimate(
            currency=profile.currency,
            measurement_type="unavailable",
            pricing_profile=profile_id,
            unavailable_reason=AvailabilityReason.NOT_EXPOSED,
            measured_quantities=raw_quantities,
            assumptions=[
                *profile.assumptions,
                "Missing service-reported quantities: "
                + ", ".join(sorted(set(invalid_metrics))),
            ],
            excluded_costs=profile.excluded_costs,
        )

    if (
        "input_tokens" in raw_quantities
        and "cached_input_tokens" in raw_quantities
        and raw_quantities["cached_input_tokens"] > raw_quantities["input_tokens"]
    ):
        return CostEstimate(
            currency=profile.currency,
            measurement_type="unavailable",
            pricing_profile=profile_id,
            unavailable_reason=AvailabilityReason.UNKNOWN,
            measured_quantities=raw_quantities,
            assumptions=[
                *profile.assumptions,
                "Inconsistent service-reported quantities: cached_input_tokens "
                "exceeds input_tokens.",
            ],
            excluded_costs=profile.excluded_costs,
        )

    quantities = {}
    for rate in mapped_rates:
        metric_name = rate.quantity_metric
        if metric_name is None:
            continue
        quantity = (
            raw_quantities["input_tokens"] - raw_quantities["cached_input_tokens"]
            if metric_name == "uncached_input_tokens"
            else raw_quantities[metric_name]
        )
        quantities[rate.meter] = quantity / rate.quantity_per_unit

    estimate = calculate_costs(
        profile,
        fixed_quantities={},
        variable_quantities=quantities,
    ).variable
    estimate.measured_quantities = raw_quantities
    if any(rate.quantity_metric == "uncached_input_tokens" for rate in mapped_rates):
        estimate.formula = (
            "variable: uncached_input_tokens = input_tokens - cached_input_tokens; "
            + (estimate.formula or "")
        )
    return estimate


def calculate_costs(
    profile: PricingProfile,
    *,
    fixed_quantities: dict[str, float],
    variable_quantities: dict[str, float],
) -> CostBreakdown:
    rates = {rate.meter: rate.unit_price for rate in profile.rates}

    def estimate(quantities: dict[str, float], layer: str) -> CostEstimate:
        unknown = sorted(set(quantities).difference(rates))
        if unknown:
            from src.benchmarking.models import AvailabilityReason

            return CostEstimate(
                measurement_type="unavailable",
                unavailable_reason=AvailabilityReason.UNKNOWN,
                assumptions=profile.assumptions,
                excluded_costs=[*profile.excluded_costs, f"Missing rates: {', '.join(unknown)}"],
            )
        amount = sum(quantity * rates[meter] for meter, quantity in quantities.items())
        formula = " + ".join(
            f"{meter}({quantity}) * rate({rates[meter]})"
            for meter, quantity in sorted(quantities.items())
        ) or "0"
        return CostEstimate(
            amount=amount,
            currency=profile.currency,
            measurement_type="estimated",
            pricing_profile=f"{profile.name}:{profile.version}",
            formula=f"{layer}: {formula}",
            measured_quantities=quantities,
            assumptions=profile.assumptions,
            excluded_costs=profile.excluded_costs,
        )

    fixed = estimate(fixed_quantities, "fixed")
    variable = estimate(variable_quantities, "variable")
    if fixed.amount is None or variable.amount is None:
        from src.benchmarking.models import AvailabilityReason

        total = CostEstimate(
            measurement_type="unavailable",
            unavailable_reason=AvailabilityReason.UNKNOWN,
            assumptions=profile.assumptions,
            excluded_costs=profile.excluded_costs,
        )
    else:
        total = CostEstimate(
            amount=fixed.amount + variable.amount,
            currency=profile.currency,
            measurement_type="estimated",
            pricing_profile=f"{profile.name}:{profile.version}",
            formula="fixed + variable",
            measured_quantities={
                "fixed_amount": fixed.amount,
                "variable_amount": variable.amount,
            },
            assumptions=profile.assumptions,
            excluded_costs=profile.excluded_costs,
        )
    return CostBreakdown(fixed=fixed, variable=variable, total=total)