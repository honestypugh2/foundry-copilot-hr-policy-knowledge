from pathlib import Path

import pytest

from src.benchmarking.adapters.agent import AgentFrameworkAdapter
from src.benchmarking.aggregation import aggregate_results
from src.benchmarking.costing import calculate_costs, calculate_token_cost
from src.benchmarking.models import (
    AvailabilityReason,
    BenchmarkCase,
    MetricValue,
    PricingProfile,
)
from src.benchmarking.runner import BenchmarkRunner
from tests.test_benchmarking_phase1 import _manifest


PROFILE_PATH = Path(
    "experiments/pricing/azure-gpt-5-mini-global-standard-2025-08-01.json"
)
CACHE_AWARE_PROFILE_PATH = Path(
    "experiments/pricing/"
    "azure-gpt-5-mini-global-standard-cache-aware-2025-08-01.json"
)


def test_gpt5_mini_profile_retains_retail_meter_provenance():
    profile = PricingProfile.model_validate_json(PROFILE_PATH.read_text())

    assert profile.version == "2025-08-01"
    assert profile.pricing_scope.endswith("Global Standard, non-batch")
    assert [rate.unit_price for rate in profile.rates] == [0.25, 2.0]
    assert [rate.unit for rate in profile.rates] == ["1M tokens", "1M tokens"]
    assert [rate.provider_meter_name for rate in profile.rates] == [
        "GPT 5 Mini Inpt Glbl 1M Tokens",
        "GPT 5 Mini outpt Glbl 1M Tokens",
    ]
    assert [rate.provider_meter_id for rate in profile.rates] == [
        "6d4c4956-4f18-535d-a63a-d56d74b1327b",
        "2d33aaf7-838f-5765-8a56-d7a7537125f5",
    ]
    assert all(rate.source_url for rate in profile.rates)
    assert all(rate.effective_date == profile.effective_date for rate in profile.rates)


def test_gpt5_mini_profile_calculates_only_supplied_token_quantities():
    profile = PricingProfile.model_validate_json(PROFILE_PATH.read_text())

    costs = calculate_costs(
        profile,
        fixed_quantities={},
        variable_quantities={
            "input_tokens_1m": 0.5,
            "output_tokens_1m": 0.25,
        },
    )

    assert costs.variable.amount == pytest.approx(0.625)
    assert costs.variable.measured_quantities == {
        "input_tokens_1m": 0.5,
        "output_tokens_1m": 0.25,
    }


def test_gpt5_mini_profile_uses_service_reported_token_quantities():
    profile = PricingProfile.model_validate_json(PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=1_000_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "output_tokens": MetricValue(
                value=1_000_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount == pytest.approx(2.25)
    assert cost.pricing_profile == "azure-gpt-5-mini-global-standard:2025-08-01"
    assert cost.measured_quantities == {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
    }


def test_gpt5_mini_profile_rejects_non_service_reported_quantities():
    profile = PricingProfile.model_validate_json(PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=1_000,
                unit="tokens",
                measurement_type="measured",
            ),
            "output_tokens": MetricValue(
                value=100,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount is None
    assert cost.unavailable_reason == AvailabilityReason.NOT_EXPOSED
    assert "input_tokens" in cost.assumptions[-1]


def test_cache_aware_profile_retains_all_retail_meter_provenance():
    profile = PricingProfile.model_validate_json(CACHE_AWARE_PROFILE_PATH.read_text())

    assert profile.name == "azure-gpt-5-mini-global-standard-cache-aware"
    assert [rate.unit_price for rate in profile.rates] == [0.25, 0.025, 2.0]
    assert [rate.provider_meter_id for rate in profile.rates] == [
        "6d4c4956-4f18-535d-a63a-d56d74b1327b",
        "4b63ead2-cde6-5970-ae20-417a7dbbfc06",
        "2d33aaf7-838f-5765-8a56-d7a7537125f5",
    ]
    assert all(rate.effective_date == "2025-08-01" for rate in profile.rates)


def test_cache_aware_profile_prices_cached_and_uncached_input_separately():
    profile = PricingProfile.model_validate_json(CACHE_AWARE_PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=1_000_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "cached_input_tokens": MetricValue(
                value=600_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "output_tokens": MetricValue(
                value=100_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount == pytest.approx(0.315)
    assert cost.measured_quantities == {
        "input_tokens": 1_000_000,
        "cached_input_tokens": 600_000,
        "output_tokens": 100_000,
    }
    assert cost.formula is not None
    assert "input_tokens - cached_input_tokens" in cost.formula


def test_cache_aware_profile_prices_zero_cached_input_as_uncached():
    profile = PricingProfile.model_validate_json(CACHE_AWARE_PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=1_000_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "cached_input_tokens": MetricValue(
                value=0,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "output_tokens": MetricValue(
                value=1_000_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount == pytest.approx(2.25)


def test_cache_aware_profile_rejects_missing_cached_input_quantity():
    profile = PricingProfile.model_validate_json(CACHE_AWARE_PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=1_000,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "output_tokens": MetricValue(
                value=100,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount is None
    assert cost.unavailable_reason == AvailabilityReason.NOT_EXPOSED
    assert "cached_input_tokens" in cost.assumptions[-1]


def test_cache_aware_profile_rejects_cached_input_above_total_input():
    profile = PricingProfile.model_validate_json(CACHE_AWARE_PROFILE_PATH.read_text())

    cost = calculate_token_cost(
        profile,
        {
            "input_tokens": MetricValue(
                value=100,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "cached_input_tokens": MetricValue(
                value=101,
                unit="tokens",
                measurement_type="service_reported",
            ),
            "output_tokens": MetricValue(
                value=10,
                unit="tokens",
                measurement_type="service_reported",
            ),
        },
    )

    assert cost.amount is None
    assert "exceeds input_tokens" in cost.assumptions[-1]


async def test_runner_reports_profiled_per_case_and_aggregate_cost():
    profile = PricingProfile.model_validate_json(PROFILE_PATH.read_text())
    profile_id = f"{profile.name}:{profile.version}"
    manifest = _manifest().model_copy(
        update={
            "pattern": "Hosted",
            "retrieval_mode": "tool",
            "pricing_profile": profile_id,
        }
    )

    async def answer(_: str):
        return {
            "status": "success",
            "answer": "Use the PTO policy.",
            "citations": [],
            "usage": {
                "input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        }

    results = await BenchmarkRunner(
        manifest,
        AgentFrameworkAdapter(answer, "tool"),
        profile,
    ).run(
        [
            BenchmarkCase(
                case_id="profiled-cost",
                query="What is PTO?",
                category="direct_fact",
                expected_behavior="answer",
            )
        ]
    )
    report = aggregate_results(results)

    assert results[0].estimated_variable_cost.amount == pytest.approx(2.25)
    assert report.variable_cost.mean_per_invocation.amount == pytest.approx(2.25)
    assert report.variable_cost.run_total.amount == pytest.approx(2.25)
    assert report.provenance["estimated_variable_cost"] == pytest.approx(2.25)
    assert report.provenance["estimated_variable_cost_statistic"] == "mean_per_invocation"