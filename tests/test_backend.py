"""Tests for the FastAPI backend endpoints."""

import os
import pytest
from unittest.mock import patch, AsyncMock

# Must set env vars before importing app
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
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data


@pytest.mark.anyio
async def test_glossary_endpoint(client: AsyncClient):
    resp = await client.get("/api/glossary")
    assert resp.status_code == 200
    data = resp.json()
    assert "glossary" in data
    assert "total" in data
    assert data["total"] > 0


@pytest.mark.anyio
async def test_azure_status_endpoint(client: AsyncClient):
    resp = await client.get("/api/azure/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ai_search" in data
    assert "openai" in data


@pytest.mark.anyio
async def test_chat_endpoint(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PATTERN", "B")
    with patch("src.backend.main.orchestrator") as mock_orch:
        mock_orch.answer_question_async = AsyncMock(return_value={
            "answer": "PTO policy allows 15 days per year.",
            "citations": [{"title": "PTO Policy", "policy_number": "50010", "excerpt": "..."}],
            "policy_references": ["Policy 50010 - PTO"],
            "confidence": 0.85,
            "matched_glossary_terms": [{"vernacular": "pto", "formal": "Paid Time Off"}],
        })

        resp = await client.post("/api/chat", json={
            "message": "What is the PTO policy?",
            "conversation_history": [],
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "citations" in data
        assert data["confidence"] > 0


@pytest.mark.anyio
async def test_chat_empty_question(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PATTERN", "B")
    with patch("src.backend.main.orchestrator") as mock_orch:
        mock_orch.answer_question_async = AsyncMock(return_value={
            "answer": "",
            "citations": [],
            "policy_references": [],
            "confidence": 0.0,
        })

        resp = await client.post("/api/chat", json={
            "message": "",
            "conversation_history": [],
        })
        # The API should still respond (orchestrator handles empty queries)
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_pattern_a_chat_normalizes_search_metadata(client: AsyncClient, monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PATTERN", "A")
    fake_hit = {
        "policy_number": "50010",
        "parentTitle": "Types of Leave: Paid Time Off",
        "content": "Employees accrue paid time off each pay period.",
    }

    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as search_service:
        search_service.return_value.search.return_value = [fake_hit]
        resp = await client.post(
            "/api/chat",
            json={"message": "What is the PTO policy?", "conversation_history": []},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["citations"] == [
        {
            "policy_number": "50010",
            "title": "Types of Leave: Paid Time Off",
        }
    ]
    assert data["policy_references"] == [
        "Policy 50010 - Types of Leave: Paid Time Off"
    ]
    assert "Employees accrue paid time off" in data["answer"]
    assert data["confidence"] == pytest.approx(0.7)


@pytest.mark.anyio
async def test_pattern_a_chat_refuses_when_search_has_no_hits(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setenv("ORCHESTRATOR_PATTERN", "A")

    with patch(
        "src.search.integrated_vectorization_search.IntegratedVectorizationSearchService"
    ) as search_service:
        search_service.return_value.search.return_value = []
        resp = await client.post(
            "/api/chat",
            json={"message": "What is the parking policy?", "conversation_history": []},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "could not find a relevant HR policy" in data["answer"]
    assert data["citations"] == []
    assert data["policy_references"] == []
    assert data["confidence"] == pytest.approx(0.0)


@pytest.mark.anyio
async def test_knowledge_base_endpoint(client: AsyncClient):
    resp = await client.get("/api/knowledge-base")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "documents" in data
