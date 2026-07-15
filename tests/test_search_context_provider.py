"""Unit tests for the Agent Framework RAG context provider builder."""

from __future__ import annotations

import importlib.util

import pytest

from src.search.agentic_context_provider import (
    RETRIEVAL_MODE_CONTEXT_AGENTIC,
    RETRIEVAL_MODE_CONTEXT_SEMANTIC,
    RETRIEVAL_MODE_TOOL,
    build_search_context_provider,
    is_context_mode,
)

_HAS_PKG = importlib.util.find_spec("agent_framework_azure_ai_search") is not None
pytestmark = pytest.mark.skipif(
    not _HAS_PKG, reason="agent_framework_azure_ai_search not installed"
)

_ENDPOINT = "https://example.search.windows.net"
_KEY = "dummy-admin-key"


def test_is_context_mode():
    assert is_context_mode(RETRIEVAL_MODE_CONTEXT_SEMANTIC)
    assert is_context_mode(RETRIEVAL_MODE_CONTEXT_AGENTIC)
    assert is_context_mode("agentic")
    assert is_context_mode("semantic")
    assert not is_context_mode(RETRIEVAL_MODE_TOOL)
    assert not is_context_mode(None)


def test_build_semantic_provider():
    provider = build_search_context_provider(
        RETRIEVAL_MODE_CONTEXT_SEMANTIC, endpoint=_ENDPOINT, api_key=_KEY
    )
    assert type(provider).__name__ == "AzureAISearchContextProvider"


def test_build_agentic_provider():
    provider = build_search_context_provider(
        RETRIEVAL_MODE_CONTEXT_AGENTIC, endpoint=_ENDPOINT, api_key=_KEY
    )
    assert type(provider).__name__ == "AzureAISearchContextProvider"


def test_build_requires_endpoint(monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    with pytest.raises(ValueError):
        build_search_context_provider("context-semantic", endpoint="", api_key=_KEY)
