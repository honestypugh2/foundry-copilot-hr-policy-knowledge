from __future__ import annotations

import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from src.backend.main import app
from src.benchmarking.api.endpoints import _publication_blockers, _summary


async def test_benchmarking_artifact_list_detail_and_comparison():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        capabilities = (await client.get("/api/benchmarking/capabilities")).json()
        listing = (await client.get("/api/benchmarking/experiments")).json()
        detail = await client.get("/api/benchmarking/experiments/synthetic-pattern-a")
        generated_detail = await client.get(
            "/api/benchmarking/experiments/synthetic-direct-search"
        )
        comparison = (await client.get(
            "/api/benchmarking/comparisons",
            params={"baseline": "synthetic-pattern-a", "candidate": "synthetic-pattern-b"},
        )).json()
        decision = (await client.get("/api/benchmarking/decisions")).json()

    assert len(capabilities["capabilities"]) == 16
    decision_capability = next(
        item
        for item in capabilities["capabilities"]
        if item["capability_id"] == "normalized-decision-contracts"
    )
    assert decision_capability["classification"] == "new_gap_coverage"
    assert decision_capability["status"] == "available"
    assert decision_capability["artifact_count"] == len(listing["items"])
    telemetry_capability = next(
        item
        for item in capabilities["capabilities"]
        if item["capability_id"] == "app-insights-agent-details"
    )
    assert telemetry_capability["authoritative_system"] == "Application Insights"
    assert telemetry_capability["deep_link_type"] == "application_insights"
    grafana_capability = next(
        item
        for item in capabilities["capabilities"]
        if item["capability_id"] == "grafana-dashboards"
    )
    assert grafana_capability["limitations"] == [
        "The Grafana resource exists, but versioned dashboards and alert rules "
        "are not yet committed."
    ]
    assert {
        "synthetic-pattern-a",
        "synthetic-pattern-b",
        "synthetic-direct-search",
    }.issubset({item["experiment_id"] for item in listing["items"]})
    assert next(
        item for item in listing["items"] if item["experiment_id"] == "synthetic-direct-search"
    )["retrieval_mode"] == "classic-hybrid"
    assert detail.status_code == 200
    assert generated_detail.status_code == 200
    assert generated_detail.json()["aggregate"]["provenance"]["fixture_mode"] is True
    assert comparison["compatible_scope"] is True
    assert comparison["deltas"]["quality"]["absolute"] > 0
    assert comparison["deltas"]["estimated_variable_cost"]["absolute"] is None
    assert decision["selected_scope"] is None
    assert len(decision["available_scopes"]) > 1
    assert set(decision["frontier_experiment_ids"]) == set()
    assert decision["recommended_experiment_id"] is None
    assert "Multiple comparable scopes are available; select one explicitly." in decision["blockers"]
    assert decision["evidence"] == []


async def test_benchmarking_artifact_ids_fail_closed():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/benchmarking/experiments/..%2Fsecret")
    assert response.status_code in {400, 404}


async def test_pattern_summary_and_native_links_fail_closed(monkeypatch):
    monkeypatch.setenv("BENCHMARK_LINK_SEARCH", "http://unsafe.example.test")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        pattern = (await client.get("/api/benchmarking/patterns/A/summary")).json()
        unknown_pattern = await client.get("/api/benchmarking/patterns/unknown/summary")
        unsafe_link = (await client.get(
            "/api/benchmarking/links/search/current"
        )).json()
        unknown_link = await client.get(
            "/api/benchmarking/links/arbitrary-resource/current"
        )

    assert pattern["item"]["automation_boundary"].startswith("automated direct Search")
    assert pattern["item"]["implementation_status"] == "implemented"
    assert pattern["item"]["evidence_status"] == "measured"
    assert pattern["item"]["latest"]["provenance"]["fixture_mode"] is False
    assert unknown_pattern.status_code == 404
    assert unsafe_link["status"] == "degraded"
    assert unsafe_link["authoritative_url"] is None
    assert unknown_link.status_code == 404


async def test_comparison_reports_incompatible_provenance():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        comparison = (await client.get(
            "/api/benchmarking/comparisons",
            params={
                "baseline": "synthetic-pattern-a",
                "candidate": "synthetic-direct-search",
            },
        )).json()

    assert comparison["compatible_scope"] is False
    assert "corpus_fingerprint differs" in comparison["incompatibility_reasons"]
    assert "measurement_boundary_class differs" in comparison["incompatibility_reasons"]


def test_native_evaluation_errors_block_publication():
    report_path = Path(
        "experiments/reports/synthetic-direct-search/"
        "synthetic-direct-search.report.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    provenance = payload["aggregate"]["provenance"]
    provenance["evaluation_release_ready"] = False
    provenance["evaluation_release_blockers"] = [
        "General quality: 1 Error and 0 Invalid results",
        "Compare meaning: 1 Error and 0 Invalid results",
    ]

    blockers = _publication_blockers(payload, _summary(payload))

    assert "General quality: 1 Error and 0 Invalid results" in blockers
    assert "Compare meaning: 1 Error and 0 Invalid results" in blockers