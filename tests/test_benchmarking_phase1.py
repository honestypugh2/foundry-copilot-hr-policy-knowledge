from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.benchmarking.adapters.direct_search import DirectSearchAdapter
from src.benchmarking.aggregation import aggregate_results
from src.benchmarking.models import (
    ActivityRecord,
    AvailabilityReason,
    BenchmarkCase,
    CostEstimate,
    ExperimentManifest,
    MetricValue,
    PricingProfile,
    PricingRate,
)
from src.benchmarking.reporting import write_jsonl, write_report_json, write_report_markdown
from src.benchmarking.runner import BenchmarkRunner


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="exp-phase1",
        created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        git_commit="abc1234",
        dirty_worktree=False,
        dataset_name="synthetic-smoke",
        dataset_version="1",
        corpus_fingerprint="sha256:corpus",
        index_fingerprint="sha256:index",
        pattern="A",
        retrieval_mode="hybrid-semantic",
        invocation_path="direct_search_sdk",
        output_mode="references",
        semantic_configuration="hr-semantic-config",
        top=3,
    )


def test_unknown_activity_round_trips_without_loss():
    raw = {
        "type": "futureActivity",
        "id": "activity-1",
        "elapsedMs": 12.5,
        "futureField": {"nested": [1, 2, 3]},
    }
    record = ActivityRecord.model_validate(raw)
    assert record.model_dump(by_alias=True, exclude_none=True) == raw


def test_missing_metric_requires_reason():
    with pytest.raises(ValueError, match="unavailable_reason"):
        MetricValue(unit="ms", measurement_type="unavailable")

    metric = MetricValue(
        unit="ms",
        measurement_type="unavailable",
        unavailable_reason=AvailabilityReason.NOT_EXPOSED,
    )
    assert metric.value is None


async def test_direct_search_contract_to_report_vertical_slice(tmp_path, monkeypatch):
    responses = {
        "PTO": [{"policy_number": "50010", "title": "Paid Time Off", "score": 3.0}],
        "Ethics": [{"policy_number": "10000", "title": "Code of Ethics", "score": 2.0}],
    }

    def fake_search(query: str, top: int):
        assert top == 3
        return responses[query]

    clock = iter([0.0, 0.010, 1.0, 1.030])
    monkeypatch.setattr("src.benchmarking.adapters.direct_search.perf_counter", lambda: next(clock))
    runner = BenchmarkRunner(_manifest(), DirectSearchAdapter(fake_search))
    cases = [
        BenchmarkCase(
            case_id="pto",
            query="PTO",
            category="direct_fact",
            expected_behavior="retrieve",
            expected_source_ids=["50010"],
        ),
        BenchmarkCase(
            case_id="ethics",
            query="Ethics",
            category="direct_fact",
            expected_behavior="retrieve",
            expected_source_ids=["10000"],
        ),
    ]

    results = await runner.run(cases)
    report = aggregate_results(results)

    assert [result.client_wall_time_ms.value for result in results] == pytest.approx([10, 30])
    assert all(result.local_metrics["recall_at_k"] == 1.0 for result in results)
    assert report.client_wall_time is not None
    assert report.client_wall_time.p50_ms == pytest.approx(20)
    assert report.client_wall_time.p95_ms == pytest.approx(29)
    assert report.client_wall_time.p99_ms == pytest.approx(29.8)
    assert report.sample_warning is not None

    jsonl_path = tmp_path / "results.jsonl"
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    write_jsonl(jsonl_path, results)
    write_report_json(json_path, _manifest(), report)
    write_report_markdown(markdown_path, _manifest(), report)

    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["service_elapsed_time_ms"]["unavailable_reason"] == "not_exposed"
    assert json.loads(json_path.read_text())["aggregate"]["count"] == 2
    markdown = markdown_path.read_text()
    assert "Controlled development experiment" in markdown
    assert "p95" in markdown


def test_manifest_schema_is_versioned_and_rejects_unknown_fields():
    schema = ExperimentManifest.model_json_schema()
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    with pytest.raises(ValueError):
        ExperimentManifest.model_validate({**_manifest().model_dump(), "secret": "nope"})


def test_pricing_is_versioned_user_input_and_unknown_cost_is_not_zero():
    profile = PricingProfile(
        name="example-input",
        version="2026-08-03",
        currency="USD",
        effective_date="2026-08-03",
        pricing_scope="user-supplied test scope",
        rates=[PricingRate(meter="input_tokens", unit="1M tokens", unit_price=1.25)],
        assumptions=["Synthetic test rate"],
        excluded_costs=["Fixed Search infrastructure"],
    )
    assert profile.schema_version == "1.0"

    unknown = CostEstimate(
        measurement_type="unavailable",
        unavailable_reason=AvailabilityReason.UNKNOWN,
    )
    assert unknown.amount is None

    with pytest.raises(ValueError, match="pricing_profile"):
        CostEstimate(measurement_type="estimated", amount=0.01, currency="USD")