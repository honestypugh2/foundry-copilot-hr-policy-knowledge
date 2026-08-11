"""Tests for the Agent Framework HR policy agent's local contracts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.agents.hr_policy_agent_af as agent_module
from src.agents.hr_policy_agent_af import (
    HR_POLICY_CONTEXT_SYSTEM_PROMPT,
    HR_POLICY_SYSTEM_PROMPT,
    HRPolicyAgent,
)


def _install_fake_framework(monkeypatch, response: str, usage_details=None):
    captured = {}

    class FakeResponseStream:
        def __aiter__(self):
            async def updates():
                yield SimpleNamespace(text=response)

            return updates()

        async def get_final_response(self):
            return SimpleNamespace(
                usage_details=usage_details or {},
                response_id="response-123",
            )

    class FakeAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self, prompt, stream=False, session=None):
            captured["prompt"] = prompt
            captured["stream"] = stream
            captured["session"] = session
            return FakeResponseStream()

    monkeypatch.setattr(agent_module, "Agent", FakeAgent)
    monkeypatch.setattr(agent_module, "FoundryChatClient", MagicMock())
    monkeypatch.setattr(agent_module, "AzureCliCredential", MagicMock())
    return captured


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            "See [Policy 50010 - Paid Time Off]. "
            "Source: [Policy 50010 - Paid Time Off]",
            [{"policy_number": "50010", "title": "Paid Time Off"}],
        ),
        (
            "Policy 50010: Paid Time Off\nPolicy 50020 - Part-time PTO",
            [
                {"policy_number": "50010", "title": "Paid Time Off"},
                {"policy_number": "50020", "title": "Part-time PTO"},
            ],
        ),
        ("Malformed [Policy 50010", []),
    ],
)
def test_extract_citations_normalizes_supported_markers(answer, expected):
    agent = HRPolicyAgent(project_endpoint="https://example.test")

    citations, policy_references = agent._extract_citations_from_text(answer)

    assert citations == expected
    assert policy_references == [
        f"Policy {citation['policy_number']} - {citation['title']}"
        for citation in expected
    ]


@pytest.mark.asyncio
async def test_tool_mode_wires_search_tool_and_tool_specific_prompt(monkeypatch):
    captured = _install_fake_framework(
        monkeypatch,
        "PTO is covered by [Policy 50010 - Paid Time Off].",
        usage_details={
            "input_token_count": 120,
            "output_token_count": 30,
            "reasoning_output_token_count": 5,
        },
    )
    agent = HRPolicyAgent(
        project_endpoint="https://example.test",
        search_endpoint="https://example.search.windows.net",
        retrieval_mode="tool",
    )
    clock = iter([1.0, 1.125, 1.5])
    monkeypatch.setattr(agent_module, "perf_counter", lambda: next(clock))

    result = await agent._generate_with_agent_framework("What is PTO?")

    assert [tool.name for tool in captured["tools"]] == ["search_hr_policies"]
    assert captured["context_providers"] is None
    assert captured["instructions"] == HR_POLICY_SYSTEM_PROMPT
    assert "Use the search_hr_policies tool" in captured["prompt"]
    assert captured["stream"] is True
    assert captured["session"].session_id == result["conversation_id"]
    assert result["citations"] == [
        {"policy_number": "50010", "title": "Paid Time Off"}
    ]
    assert result["confidence"] == pytest.approx(0.85)
    assert result["usage"] == {
        "input_tokens": 120,
        "output_tokens": 30,
        "reasoning_tokens": 5,
    }
    assert result["response_id"] == "response-123"
    assert result["timings"] == {
        "ttft_ms": pytest.approx(125),
        "ttlt_ms": pytest.approx(500),
        "stream_duration_ms": pytest.approx(375),
    }


@pytest.mark.asyncio
async def test_context_mode_wires_provider_without_duplicate_search_tool(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")
    captured = _install_fake_framework(
        monkeypatch, "Part-time PTO is covered by [Policy 50020 - Part-time PTO]."
    )
    provider = object()
    import src.search.agentic_context_provider as context_module

    build_provider = MagicMock(return_value=provider)
    monkeypatch.setattr(context_module, "build_search_context_provider", build_provider)
    agent = HRPolicyAgent(
        project_endpoint="https://example.test",
        search_endpoint="https://example.search.windows.net",
        search_api_key="test-key",
        search_index_name="hr-policy-index",
        retrieval_mode="context-agentic",
    )

    await agent._generate_with_agent_framework("How does part-time PTO work?")

    assert captured["tools"] == []
    assert captured["context_providers"] == [provider]
    assert captured["instructions"] == HR_POLICY_CONTEXT_SYSTEM_PROMPT
    assert "Use the search_hr_policies tool" not in captured["prompt"]
    build_provider.assert_called_once_with(
        "context-agentic",
        endpoint="https://example.search.windows.net",
        index_name="hr-policy-index",
        api_key="test-key",
        top_k=agent._top_k,
    )


@pytest.mark.asyncio
async def test_context_provider_failure_rejects_mislabeled_run(monkeypatch):
    _install_fake_framework(monkeypatch, "No matching policy was found.")
    import src.search.agentic_context_provider as context_module

    monkeypatch.setattr(
        context_module,
        "build_search_context_provider",
        MagicMock(side_effect=RuntimeError("provider unavailable")),
    )
    agent = HRPolicyAgent(
        project_endpoint="https://example.test",
        search_endpoint="https://example.search.windows.net",
        retrieval_mode="context-semantic",
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to initialize requested retrieval mode 'context-semantic'",
    ):
        await agent._generate_with_agent_framework("Find an HR policy")


def test_invalid_retrieval_mode_is_rejected():
    with pytest.raises(ValueError, match="Unsupported RETRIEVAL_MODE"):
        HRPolicyAgent(
            project_endpoint="https://example.test",
            retrieval_mode="semantic-typo",
        )


def test_managed_identity_ignores_stale_search_key(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "true")
    monkeypatch.setenv("AZURE_SEARCH_API_KEY", "rotated-key")

    agent = HRPolicyAgent(project_endpoint="https://example.test")

    assert agent.search_api_key is None


def test_search_tool_emits_policy_excerpt_and_document_location(monkeypatch):
    search_client = MagicMock()
    search_client.search.return_value = [
        {
            "policy_number": "50010",
            "parent_title": "Types of Leave: Paid Time Off",
            "policy": "Employees accrue paid time off each pay period.",
            "blob_url": "https://example.blob.core.windows.net/hr/50010.pdf",
            "@search.score": 7.5,
            "@search.reranker_score": 3.2,
        }
    ]
    search_client_type = MagicMock(return_value=search_client)
    vector_query = object()
    vector_query_type = MagicMock(return_value=vector_query)
    monkeypatch.setattr(agent_module, "SearchClient", search_client_type)
    monkeypatch.setattr(agent_module, "VectorizableTextQuery", vector_query_type)
    monkeypatch.setattr(
        agent_module,
        "expand_query_with_glossary",
        MagicMock(return_value="pto Paid Time Off"),
    )
    agent = HRPolicyAgent(
        project_endpoint="https://example.test",
        search_endpoint="https://example.search.windows.net",
        search_api_key="test-key",
        retrieval_mode="tool",
    )

    output = agent.search_hr_policies.func(agent, "pto")

    assert "Policy 50010 - Types of Leave: Paid Time Off" in output
    assert "Employees accrue paid time off each pay period." in output
    assert "https://example.blob.core.windows.net/hr/50010.pdf" in output
    search_client.search.assert_called_once_with(
        search_text="pto Paid Time Off",
        query_type="semantic",
        top=agent._top_k,
        semantic_configuration_name=agent.semantic_configuration_name,
        vector_queries=[vector_query],
    )