"""
Agent Framework RAG context providers for the HR policy agent.

Wraps ``agent_framework_azure_ai_search.AzureAISearchContextProvider`` — the
out-of-the-box Agent Framework RAG context provider (the Python counterpart of
``TextSearchProvider``). It runs retrieval automatically **before each model
invocation** and injects standardized context + citation prompts, so the agent
no longer has to call a search tool explicitly.

It supports two retrieval modes, both reusing the same Azure AI Search assets
this repo already provisions:

- ``semantic`` — **classic search** (index-first hybrid + semantic ranker) over
  ``hr-policy-index``.
- ``agentic`` — **agentic retrieval** over the Foundry IQ knowledge base
  ``hr-knowledge-base`` (LLM-planned sub-queries, merged results).

This is what lets the Agent Framework / Hosted Agent path support *both* classic
and agentic RAG, matching the Foundry Agent Service path.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, cast

from src.config.search_config import search_cfg

logger = logging.getLogger(__name__)

# RETRIEVAL_MODE values understood by the Agent Framework path.
RETRIEVAL_MODE_TOOL = "tool"  # custom @tool classic search (default)
RETRIEVAL_MODE_CONTEXT_SEMANTIC = "context-semantic"  # provider, classic search
RETRIEVAL_MODE_CONTEXT_AGENTIC = "context-agentic"  # provider, agentic retrieval

_CONTEXT_MODES = frozenset(
    {
        RETRIEVAL_MODE_CONTEXT_SEMANTIC,
        RETRIEVAL_MODE_CONTEXT_AGENTIC,
        "semantic",
        "agentic",
    }
)

# search_config.json output_mode -> provider literal.
_OUTPUT_MODE_MAP = {
    "EXTRACTIVE": "extractive_data",
    "EXTRACTIVE_DATA": "extractive_data",
    "ANSWER_SYNTHESIS": "answer_synthesis",
    "ANSWERSYNTHESIS": "answer_synthesis",
}

_VALID_EFFORTS = frozenset({"minimal", "medium", "low"})


def is_context_mode(mode: Optional[str]) -> bool:
    """Return True if ``mode`` selects the out-of-the-box context provider."""
    return (mode or "").lower() in _CONTEXT_MODES


def _supports_higher_reasoning_effort() -> bool:
    """True when the installed azure-search-documents allows non-minimal effort.

    The GA ``azure-search-documents`` (12.0.0, pinned by this repo) only supports
    ``retrieval_reasoning_effort='minimal'``. ``medium`` / ``low`` require a
    preview build (>= 12.1.0b*). We clamp to ``minimal`` on GA to avoid a
    runtime ``ValueError`` from the context provider.
    """
    try:
        import azure.search.documents as asd

        version = getattr(asd, "__version__", "0.0.0")
        if any(marker in version for marker in ("a", "b", "rc")):
            return True
        parts = version.split(".")
        major = int(parts[0])
        minor = int("".join(ch for ch in parts[1] if ch.isdigit()) or "0")
        return (major, minor) >= (12, 1)
    except Exception:  # pragma: no cover - defensive
        return False


def _resolve_credential() -> Any:
    from azure.identity import AzureCliCredential, DefaultAzureCredential

    try:
        return AzureCliCredential(process_timeout=30)
    except Exception:  # pragma: no cover
        return DefaultAzureCredential()


def build_search_context_provider(
    mode: str,
    *,
    endpoint: Optional[str] = None,
    index_name: Optional[str] = None,
    api_key: Optional[str] = None,
    top_k: Optional[int] = None,
) -> Any:
    """Build an ``AzureAISearchContextProvider`` for classic or agentic RAG.

    Args:
        mode: ``"context-semantic"``/``"semantic"`` for classic index search, or
            ``"context-agentic"``/``"agentic"`` for Foundry IQ knowledge-base
            agentic retrieval.
        endpoint: Azure AI Search endpoint (falls back to ``AZURE_SEARCH_ENDPOINT``).
        index_name: Index for semantic mode (defaults to ``search_cfg.index_name``).
        api_key: Optional admin/query key; when absent, Entra ID credential is used.
        top_k: Result count (defaults to ``search_cfg.top_k``).

    Returns:
        A configured ``AzureAISearchContextProvider``.
    """
    from agent_framework_azure_ai_search import AzureAISearchContextProvider

    endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if not endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is required to build the search context provider."
        )

    key = api_key if (api_key and not api_key.startswith("your_")) else None
    common: dict[str, Any] = {"endpoint": endpoint, "top_k": top_k or search_cfg.top_k}
    if key:
        common["api_key"] = key
    else:
        common["credential"] = _resolve_credential()

    if mode.lower().endswith("agentic"):
        ar = search_cfg.agentic_retrieval
        output_mode = _OUTPUT_MODE_MAP.get(
            str(ar.get("output_mode", "EXTRACTIVE")).upper(), "extractive_data"
        )
        effort = str(ar.get("retrieval_reasoning_effort", "medium")).lower()
        if effort not in _VALID_EFFORTS:
            effort = "medium"
        # GA azure-search-documents (12.0.0) only supports 'minimal'.
        if effort != "minimal" and not _supports_higher_reasoning_effort():
            logger.info(
                "azure-search-documents GA build detected; clamping "
                "retrieval_reasoning_effort '%s' -> 'minimal'.",
                effort,
            )
            effort = "minimal"
        logger.info(
            "Agent Framework RAG: agentic retrieval over knowledge base '%s'",
            search_cfg.knowledge_base_name,
        )
        return AzureAISearchContextProvider(
            mode="agentic",
            knowledge_base_name=search_cfg.knowledge_base_name,
            knowledge_base_output_mode=cast(Any, output_mode),
            retrieval_reasoning_effort=cast(Any, effort),
            **common,
        )

    logger.info(
        "Agent Framework RAG: classic (semantic) search over index '%s'",
        search_cfg.index_name,
    )
    # Note: vector_field_name is intentionally omitted. This index uses a
    # server-side AzureOpenAIVectorizer (integrated vectorization), so the
    # provider issues a vectorizable query and applies the semantic ranker;
    # passing vector_field_name would force a client-side embedding_function.
    return AzureAISearchContextProvider(
        mode="semantic",
        index_name=index_name or search_cfg.index_name,
        semantic_configuration_name=search_cfg.semantic_configuration,
        **common,
    )
