"""Tests for the POST /api/lookup endpoint (Pattern C document locator).

Mocks ``IntegratedVectorizationSearchService.search`` so the test runs
fully offline and verifies that metadata fields from the index are
passed through to the response shape that
``copilot/openapi-lookup-v2.json`` (and the canonical
``file_metadata_lookup`` tool from the reference repo) expects.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Must set env vars before importing the app
os.environ.setdefault("AZURE_AI_SEARCH_ENDPOINT", "https://test.search.windows.net")
os.environ.setdefault("AZURE_AI_SEARCH_API_KEY", "test-key")

from httpx import AsyncClient, ASGITransport
from src.backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_lookup_returns_canonical_metadata_fields(client: AsyncClient):
    """Each document in the response includes the six metadata fields
    that mirror the reference repo's ``file_metadata_lookup`` tool.
    """
    fake_hit = {
        "policy_number": "51350",
        "parentTitle": "Types of Leave: Paid Time Off (PTO)",
        "fileName": "51350 - Types of Leave_ Paid Time Off (PTO) (23472_2).pdf",
        "filePath": "https://example.blob.core.windows.net/hr-policies/51350.pdf",
        "blob_url": "https://example.blob.core.windows.net/hr-policies/51350.pdf",
        "score": 12.34,
    }

    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_instance.search.return_value = [fake_hit]
        mock_cls.return_value = mock_instance

        resp = await client.post("/api/lookup", json={"message": "PTO policy"})

    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] == 1
    assert body["query"] == "PTO policy"
    assert "expanded_query" in body
    assert "processing_time_ms" in body
    assert isinstance(body["documents"], list) and len(body["documents"]) == 1

    doc = body["documents"][0]
    # All six canonical metadata fields are present and pass-through.
    assert doc["policy_number"] == "51350"
    assert doc["parent_title"] == "Types of Leave: Paid Time Off (PTO)"
    assert doc["metadata_storage_name"].endswith(".pdf")
    assert doc["metadata_storage_path"].startswith("https://")
    assert doc["blob_url"].startswith("https://")
    assert doc["score"] == pytest.approx(12.34)


@pytest.mark.anyio
async def test_lookup_empty_results(client: AsyncClient):
    """When the index returns no hits, the response shape is still
    well-formed with ``total: 0`` and an empty ``documents`` array.
    """
    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_cls.return_value = mock_instance

        resp = await client.post("/api/lookup", json={"message": "nonexistent policy"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["documents"] == []


@pytest.mark.anyio
async def test_lookup_search_service_unavailable(client: AsyncClient):
    """If the IV search client cannot be constructed, return 503 \u2014 not 500.
    Matches the contract documented in ``copilot/openapi-lookup-v2.json``.
    """
    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as mock_cls:
        mock_cls.side_effect = RuntimeError("search endpoint not configured")

        resp = await client.post("/api/lookup", json={"message": "PTO"})

    assert resp.status_code == 503


@pytest.mark.anyio
async def test_lookup_passes_glossary_expanded_query(client: AsyncClient):
    """The endpoint forwards the glossary-expanded query (not the raw
    user query) to the search client, matching ``/api/chat`` behavior.
    """
    captured: dict = {}

    def fake_search(query: str, top: int = 3):
        captured["query"] = query
        captured["top"] = top
        return []

    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_instance.search.side_effect = fake_search
        mock_cls.return_value = mock_instance

        resp = await client.post("/api/lookup", json={"message": "pto"})

    assert resp.status_code == 200
    # ``pto`` should be expanded to include ``Paid Time Off`` by the glossary.
    assert "paid time off" in captured["query"].lower()
    assert captured["top"] == 3
