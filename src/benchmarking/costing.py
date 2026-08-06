"""Versioned fixed and variable cost estimation from user-supplied rates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.benchmarking.models import CostEstimate, PricingProfile


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed: CostEstimate
    variable: CostEstimate
    total: CostEstimate


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