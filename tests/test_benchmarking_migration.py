from __future__ import annotations

import pytest

from src.benchmarking.activity import parse_activity, summarize_activity
from src.benchmarking.aggregation import aggregate_results
from src.benchmarking.costing import calculate_costs
from src.benchmarking.decision import (
    DecisionCandidate,
    SloThresholds,
    pareto_frontier,
    qualify_slos,
)
from src.benchmarking.evaluation import (
    EvaluationCategory,
    apply_deterministic_evaluation,
    retrieval_metrics,
)
from src.benchmarking.models import (
    ActivityRecord,
    MetricValue,
    PricingProfile,
    PricingRate,
    StageTiming,
)
from src.benchmarking.adapters import DirectSearchAdapter
from src.benchmarking.models import BenchmarkCase
from src.benchmarking.runner import BenchmarkRunner
from tests.test_benchmarking_phase1 import _manifest


def test_activity_normalization_is_lossless_and_does_not_sum_elapsed_time():
    raw = [
        {"type": "searchIndex", "id": 1, "elapsedMs": 118, "count": 6},
        {"type": "searchIndex", "id": 2, "elapsed_ms": 78, "future": True},
        {"type": "futureActivity", "id": "x", "input_tokens": 7},
        "junk",
    ]
    records = parse_activity(raw)
    assert records[1].model_dump(by_alias=True, exclude_none=True)["future"] is True
    assert records[1].elapsed_ms == 78
    summary = summarize_activity(records)
    assert summary["searchIndex"]["records"] == 2
    assert "elapsed_ms" not in summary["searchIndex"]


def test_eight_category_taxonomy_and_target_source_metrics():
    assert len(EvaluationCategory) == 8
    metrics = retrieval_metrics(["50020", "50010", "10000"], ["50010", "50020"])
    assert metrics["recall_at_1"] == 0.5
    assert metrics["recall_at_3"] == 1.0
    assert metrics["precision_at_3"] == 2 / 3
    assert metrics["mrr"] == 1.0


async def test_cold_warm_and_error_aggregation_use_client_wall_time_only(monkeypatch):
    clock = iter([0.0, 0.030, 1.0, 1.010])
    monkeypatch.setattr("src.benchmarking.adapters.direct_search.perf_counter", lambda: next(clock))
    results = await BenchmarkRunner(
        _manifest(),
        DirectSearchAdapter(lambda query, top: [{"policy_number": "50010"}]),
    ).run([
        BenchmarkCase(
            case_id="cold",
            query="PTO",
            category="direct_fact",
            expected_behavior="retrieve",
            expected_source_ids=["50010"],
        ),
        BenchmarkCase(
            case_id="warm",
            query="PTO",
            category="direct_fact",
            expected_behavior="retrieve",
            expected_source_ids=["50010"],
        ),
    ])
    results[0] = results[0].model_copy(update={"temperature": "cold"})
    results[1] = results[1].model_copy(
        update={
            "temperature": "warm",
            "stage_timings": [
                StageTiming(
                    name="search_call",
                    duration_ms=MetricValue(
                        value=8.0,
                        unit="ms",
                        measurement_type="measured",
                    ),
                )
            ],
            "activity": [
                ActivityRecord(
                    type="searchIndex",
                    elapsedMs=7.0,
                    inputTokens=4,
                ),
                ActivityRecord(type="searchIndex", elapsedMs=5.0),
            ],
        }
    )
    failed = results[1].model_copy(
        update={
            "case_id": "failed",
            "status": "error",
            "error_classification": "SyntheticFailure",
            "client_wall_time_ms": results[1].client_wall_time_ms.model_copy(
                update={"value": 1000.0}
            ),
        }
    )
    results.append(failed)
    report = aggregate_results(results)
    assert report.count == 3
    assert report.error_rate == pytest.approx(1 / 3)
    assert report.client_wall_time.count == 2
    assert report.cold_client_wall_time.p50_ms == pytest.approx(30)
    assert report.warm_client_wall_time.p50_ms == pytest.approx(10)
    assert report.client_wall_time.standard_deviation_ms == pytest.approx(10)
    assert report.by_category["direct_fact"].count == 2
    assert report.by_stage["search_call"].p50_ms == 8
    assert report.by_activity_type["searchIndex"].record_count == 2
    assert report.by_activity_type["searchIndex"].elapsed_ms.p50_ms == 6
    assert report.by_activity_type["searchIndex"].input_tokens == 4
    assert results[0].local_metrics["recall_at_1"] == 1.0
    assert results[0].local_metrics["mrr"] == 1.0
    assert not hasattr(report, "activity_total")
    assert not hasattr(report, "overhead")


def test_fixed_and_variable_costs_remain_separate_and_user_supplied():
    profile = PricingProfile(
        name="sanitized-scenario",
        version="1",
        currency="USD",
        effective_date="2026-08-03",
        pricing_scope="synthetic test only",
        rates=[
            PricingRate(meter="search_units", unit="unit-month", unit_price=10),
            PricingRate(meter="output_tokens", unit="token", unit_price=0.01),
        ],
        assumptions=["Test values are not Azure prices"],
        excluded_costs=["Copilot Studio licensing"],
    )
    costs = calculate_costs(
        profile,
        fixed_quantities={"search_units": 2},
        variable_quantities={"output_tokens": 100},
    )
    assert costs.fixed.amount == 20
    assert costs.variable.amount == 1
    assert costs.total.amount == 21
    assert costs.fixed.formula.startswith("fixed:")


async def test_existing_deterministic_graders_join_normalized_metrics(monkeypatch):
    clock = iter([0.0, 0.01])
    monkeypatch.setattr("src.benchmarking.adapters.direct_search.perf_counter", lambda: next(clock))
    result = (await BenchmarkRunner(
        _manifest(),
        DirectSearchAdapter(
            lambda query, top: [{
                "policy_number": "50010",
                "title": "Types of Leave: Paid Time Off (PTO)",
            }]
        ),
    ).run([BenchmarkCase(
        case_id="pto-accrual",
        query="How much PTO?",
        category="direct_fact",
        expected_behavior="retrieve",
        expected_source_ids=["50010"],
    )]))[0]
    graded = apply_deterministic_evaluation(
        result,
        answer="Per Policy 50010, Paid Time Off is described here.",
        expected_policy_number="50010",
        expected_policy_title="Types of Leave: Paid Time Off (PTO)",
    )
    assert graded.local_metrics["policy_number_cited"] is True
    assert graded.local_metrics["deterministic_pass"] is True


def test_pareto_and_slo_decisions_reject_unknowns_and_explain_failures():
    candidates = [
        DecisionCandidate(
            configuration_id="A",
            quality=0.90,
            latency_p95_ms=100,
            success_rate=0.99,
            security_pass_rate=1.0,
            estimated_variable_cost=0.03,
            comparison_scope="fixture-v1",
        ),
        DecisionCandidate(
            configuration_id="B",
            quality=0.80,
            latency_p95_ms=120,
            success_rate=0.98,
            security_pass_rate=1.0,
            estimated_variable_cost=0.04,
            comparison_scope="fixture-v1",
        ),
        DecisionCandidate(
            configuration_id="unknown-cost",
            quality=0.95,
            latency_p95_ms=90,
            success_rate=1.0,
            security_pass_rate=1.0,
            comparison_scope="fixture-v1",
        ),
    ]
    assert pareto_frontier(candidates) == ["A"]
    qualifications = qualify_slos(
        candidates,
        SloThresholds(
            minimum_quality=0.85,
            maximum_latency_p95_ms=110,
            minimum_success_rate=0.99,
            minimum_security_pass_rate=1.0,
            maximum_estimated_variable_cost=0.035,
        ),
    )
    assert qualifications[0].qualified
    assert "quality: threshold failed" in qualifications[1].failures
    assert "estimated_variable_cost: unavailable" in qualifications[2].failures