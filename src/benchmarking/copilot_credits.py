"""Copilot Studio Copilot Credits cost lane.

Copilot Studio bills in Copilot Credits, the common currency across Copilot
Studio capabilities, and exposes no stable public per-agent consumption REST
API. Credits are rated per agent activity (classic answer, generative answer,
agent action, and so on), not per chat message, so this module estimates per
benchmark interaction and multiplies by the interaction count. This module
provides the two honest, automatable halves of that cost lane:

1. A deterministic forward ESTIMATE of Credits-per-interaction from each agent's
   known configuration (rate card x per-pattern feature mix) - mirroring the
   Microsoft Copilot Studio agent usage estimator.
2. A RECONCILIATION ingester for the authoritative billed Credits exported from
   the Power Platform admin center consumption grid (analogous to Azure Cost
   Management for the Foundry per-token lane).

Credits never convert to tokens or USD; keep them on a separate axis.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CreditEventLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meter: str
    count: float
    credits_each: float
    credits_subtotal: float
    uncertain: bool = False


class CreditEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str | None
    front_door_agent: str | None
    interactions: int
    credits_per_interaction: float
    estimated_total_credits: float
    lines: list[CreditEventLine]
    byo_foundry_tokens: bool
    rate_profile: str
    feature_mix_profile: str
    has_uncertain_events: bool
    assumptions: list[str]


class AdminConsumptionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    credits: float
    period: str | None = None
    meter: str | None = None


class Reconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str | None
    front_door_agent: str | None
    estimated_total_credits: float
    billed_total_credits: float
    delta_credits: float
    delta_pct: float | None
    note: str


def load_rate_card(path: Path) -> tuple[dict[str, float], dict]:
    """Return (meter -> credits) and the full rate-card profile."""
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    rates = {
        str(rate["meter"]): float(rate["credits"])
        for rate in profile.get("rates", [])
    }
    if not rates:
        raise ValueError(f"Rate card {path} has no rates")
    return rates, profile


def load_feature_mix(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def estimate_interaction_credits(
    events: list[dict], rate_card: dict[str, float], uncertain_meters: set[str]
) -> tuple[float, list[CreditEventLine]]:
    lines: list[CreditEventLine] = []
    total = 0.0
    for event in events:
        meter = str(event["meter"])
        if meter not in rate_card:
            raise ValueError(f"Unknown meter {meter!r} not in rate card")
        count = float(event.get("count", 1))
        each = rate_card[meter]
        subtotal = each * count
        total += subtotal
        lines.append(
            CreditEventLine(
                meter=meter,
                count=count,
                credits_each=each,
                credits_subtotal=subtotal,
                uncertain=meter in uncertain_meters,
            )
        )
    return total, lines


def estimate_pattern(
    pattern: str,
    *,
    rate_card_path: Path,
    feature_mix_path: Path,
    interactions: int = 1,
) -> CreditEstimate:
    rate_card, rate_profile = load_rate_card(rate_card_path)
    mix = load_feature_mix(feature_mix_path)
    patterns = mix.get("patterns", {})
    if pattern not in patterns:
        raise ValueError(
            f"Pattern {pattern!r} not in feature mix; known: {sorted(patterns)}"
        )
    spec = patterns[pattern]
    uncertain = set(spec.get("uncertain_events", []))
    per_interaction, lines = estimate_interaction_credits(
        spec.get("events", []), rate_card, uncertain
    )
    rate_id = f"{rate_profile['name']}:{rate_profile['version']}"
    return CreditEstimate(
        pattern=pattern,
        front_door_agent=spec.get("front_door_agent"),
        interactions=interactions,
        credits_per_interaction=per_interaction,
        estimated_total_credits=per_interaction * interactions,
        lines=lines,
        byo_foundry_tokens=bool(spec.get("byo_foundry_tokens", False)),
        rate_profile=rate_id,
        feature_mix_profile=f"{mix['name']}:{mix['version']}",
        has_uncertain_events=any(line.uncertain for line in lines),
        assumptions=[*rate_profile.get("assumptions", []), *mix.get("assumptions", [])],
    )


def parse_consumption_csv(path: Path) -> list[AdminConsumptionRow]:
    """Parse a normalized consumption CSV exported from the admin-center grid.

    Expected columns (case-insensitive): agent, credits, and optionally period
    and meter. Save the Power Platform admin center consumption grid rows to a
    CSV with these headers before running reconciliation.
    """
    rows: list[AdminConsumptionRow] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}
        if "agent" not in headers or "credits" not in headers:
            raise ValueError(
                "Consumption CSV must have 'agent' and 'credits' columns; "
                f"found {list(headers)}"
            )
        for raw in reader:
            rows.append(
                AdminConsumptionRow(
                    agent=str(raw[headers["agent"]]).strip(),
                    credits=float(raw[headers["credits"]]),
                    period=(
                        str(raw[headers["period"]]).strip()
                        if "period" in headers
                        else None
                    ),
                    meter=(
                        str(raw[headers["meter"]]).strip()
                        if "meter" in headers
                        else None
                    ),
                )
            )
    if not rows:
        raise ValueError(f"Consumption CSV {path} has no data rows")
    return rows


def reconcile(
    estimate: CreditEstimate, consumption: list[AdminConsumptionRow]
) -> Reconciliation:
    billed = sum(
        row.credits
        for row in consumption
        if estimate.front_door_agent
        and row.agent.strip().lower() == estimate.front_door_agent.strip().lower()
    )
    delta = estimate.estimated_total_credits - billed
    delta_pct = (delta / billed * 100.0) if billed else None
    note = (
        "Billed Credits from the Power Platform admin center consumption grid are "
        "authoritative; the estimate is a forward figure from configuration."
    )
    if billed == 0:
        note = (
            "No billed rows matched the front-door agent name; confirm the agent "
            "label in the exported consumption grid."
        )
    return Reconciliation(
        pattern=estimate.pattern,
        front_door_agent=estimate.front_door_agent,
        estimated_total_credits=estimate.estimated_total_credits,
        billed_total_credits=billed,
        delta_credits=delta,
        delta_pct=delta_pct,
        note=note,
    )
