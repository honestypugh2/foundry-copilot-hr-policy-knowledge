"""Pareto and SLO decisions over comparable normalized configurations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DecisionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_id: str
    quality: float | None = Field(default=None, ge=0, le=1)
    latency_p95_ms: float | None = Field(default=None, ge=0)
    success_rate: float | None = Field(default=None, ge=0, le=1)
    security_pass_rate: float | None = Field(default=None, ge=0, le=1)
    estimated_variable_cost: float | None = Field(default=None, ge=0)
    comparison_scope: str


class SloThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_quality: float = Field(ge=0, le=1)
    maximum_latency_p95_ms: float = Field(ge=0)
    minimum_success_rate: float = Field(ge=0, le=1)
    minimum_security_pass_rate: float = Field(ge=0, le=1)
    maximum_estimated_variable_cost: float = Field(ge=0)


class Qualification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_id: str
    qualified: bool
    failures: list[str]


def pareto_frontier(candidates: list[DecisionCandidate]) -> list[str]:
    """Return non-dominated IDs; candidates must share scope and all metrics."""
    eligible = [candidate for candidate in candidates if _complete(candidate)]
    scopes = {candidate.comparison_scope for candidate in eligible}
    if len(scopes) > 1:
        raise ValueError("Pareto candidates must have the same comparison scope")

    frontier: list[str] = []
    for candidate in eligible:
        dominated = any(
            other.configuration_id != candidate.configuration_id
            and _dominates(other, candidate)
            for other in eligible
        )
        if not dominated:
            frontier.append(candidate.configuration_id)
    return sorted(frontier)


def qualify_slos(
    candidates: list[DecisionCandidate], thresholds: SloThresholds
) -> list[Qualification]:
    qualifications: list[Qualification] = []
    for candidate in candidates:
        failures: list[str] = []
        checks = (
            ("quality", candidate.quality, lambda value: value >= thresholds.minimum_quality),
            (
                "latency_p95_ms",
                candidate.latency_p95_ms,
                lambda value: value <= thresholds.maximum_latency_p95_ms,
            ),
            (
                "success_rate",
                candidate.success_rate,
                lambda value: value >= thresholds.minimum_success_rate,
            ),
            (
                "security_pass_rate",
                candidate.security_pass_rate,
                lambda value: value >= thresholds.minimum_security_pass_rate,
            ),
            (
                "estimated_variable_cost",
                candidate.estimated_variable_cost,
                lambda value: value <= thresholds.maximum_estimated_variable_cost,
            ),
        )
        for metric, value, check in checks:
            if value is None:
                failures.append(f"{metric}: unavailable")
            elif not check(value):
                failures.append(f"{metric}: threshold failed")
        qualifications.append(
            Qualification(
                configuration_id=candidate.configuration_id,
                qualified=not failures,
                failures=failures,
            )
        )
    return qualifications


def _complete(candidate: DecisionCandidate) -> bool:
    return all(
        value is not None
        for value in (
            candidate.quality,
            candidate.latency_p95_ms,
            candidate.success_rate,
            candidate.security_pass_rate,
            candidate.estimated_variable_cost,
        )
    )


def _dominates(left: DecisionCandidate, right: DecisionCandidate) -> bool:
    left_values = (
        left.quality,
        -left.latency_p95_ms,
        left.success_rate,
        left.security_pass_rate,
        -left.estimated_variable_cost,
    )
    right_values = (
        right.quality,
        -right.latency_p95_ms,
        right.success_rate,
        right.security_pass_rate,
        -right.estimated_variable_cost,
    )
    return all(a >= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a > b for a, b in zip(left_values, right_values, strict=True)
    )