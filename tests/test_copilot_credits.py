"""Tests for the Copilot Credits cost lane."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.benchmarking.copilot_credits import (
    estimate_pattern,
    load_rate_card,
    parse_consumption_csv,
    reconcile,
)

RATE_CARD = Path(
    "experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json"
)
FEATURE_MIX = Path("experiments/pricing/copilot-studio-credits-feature-mix.json")


def test_rate_card_has_core_meters() -> None:
    rates, profile = load_rate_card(RATE_CARD)
    assert rates["classic_answer"] == 1
    assert rates["generative_answer"] == 2
    assert rates["agent_action"] == 5
    assert rates["tenant_graph_grounding"] == 10
    assert profile["currency"] == "CREDITS"


def test_pattern_a_is_one_generative_answer() -> None:
    estimate = estimate_pattern("A", rate_card_path=RATE_CARD, feature_mix_path=FEATURE_MIX)
    assert estimate.credits_per_interaction == 2
    assert estimate.byo_foundry_tokens is False
    assert estimate.has_uncertain_events is False


def test_pattern_c_generative_plus_action_scales_with_interactions() -> None:
    estimate = estimate_pattern(
        "C", rate_card_path=RATE_CARD, feature_mix_path=FEATURE_MIX, interactions=35
    )
    assert estimate.credits_per_interaction == 7  # 2 generative + 5 agent action
    assert estimate.estimated_total_credits == 7 * 35
    assert estimate.has_uncertain_events is True


def test_hosted_flags_separate_foundry_token_lane() -> None:
    estimate = estimate_pattern(
        "Hosted", rate_card_path=RATE_CARD, feature_mix_path=FEATURE_MIX
    )
    assert estimate.byo_foundry_tokens is True


def test_unknown_pattern_raises() -> None:
    with pytest.raises(ValueError):
        estimate_pattern("Z", rate_card_path=RATE_CARD, feature_mix_path=FEATURE_MIX)


def test_reconcile_matches_billed_agent(tmp_path: Path) -> None:
    csv_path = tmp_path / "consumption.csv"
    csv_path.write_text(
        "agent,credits,period\nAsk HR Policy Agent C,300,2026-08\nOther Agent,999,2026-08\n",
        encoding="utf-8",
    )
    estimate = estimate_pattern(
        "C", rate_card_path=RATE_CARD, feature_mix_path=FEATURE_MIX, interactions=35
    )
    result = reconcile(estimate, parse_consumption_csv(csv_path))
    assert result.billed_total_credits == 300
    assert result.estimated_total_credits == 245
    assert result.delta_credits == -55


def test_consumption_csv_requires_columns(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("name,value\nx,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_consumption_csv(bad)
