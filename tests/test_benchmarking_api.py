from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from src.backend.main import app


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

    assert capabilities["capabilities"][0]["status"] == "available"
    assert len(listing["items"]) == 3
    assert detail.status_code == 200
    assert generated_detail.status_code == 200
    assert generated_detail.json()["aggregate"]["provenance"]["fixture_mode"] is True
    assert comparison["compatible_scope"] is True
    assert comparison["deltas"]["quality"]["absolute"] > 0
    assert comparison["deltas"]["estimated_variable_cost"]["absolute"] is None


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