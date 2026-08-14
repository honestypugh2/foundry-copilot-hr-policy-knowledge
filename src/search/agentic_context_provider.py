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

_RETRIEVAL_MODE_ALIASES = {
    RETRIEVAL_MODE_TOOL: RETRIEVAL_MODE_TOOL,
    RETRIEVAL_MODE_CONTEXT_SEMANTIC: RETRIEVAL_MODE_CONTEXT_SEMANTIC,
    RETRIEVAL_MODE_CONTEXT_AGENTIC: RETRIEVAL_MODE_CONTEXT_AGENTIC,
    "semantic": RETRIEVAL_MODE_CONTEXT_SEMANTIC,
    "agentic": RETRIEVAL_MODE_CONTEXT_AGENTIC,
}

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


def normalize_retrieval_mode(mode: Optional[str]) -> str:
    """Return a canonical retrieval mode or reject an unknown value."""
    candidate = (mode or RETRIEVAL_MODE_TOOL).strip().lower()
    try:
        return _RETRIEVAL_MODE_ALIASES[candidate]
    except KeyError as exc:
        valid = ", ".join(
            (
                RETRIEVAL_MODE_TOOL,
                RETRIEVAL_MODE_CONTEXT_SEMANTIC,
                RETRIEVAL_MODE_CONTEXT_AGENTIC,
            )
        )
        raise ValueError(
            f"Unsupported RETRIEVAL_MODE {candidate!r}; expected one of: {valid}"
        ) from exc


def _resolve_credential() -> Any:
    from azure.identity import AzureCliCredential, DefaultAzureCredential

    try:
        return AzureCliCredential(process_timeout=30)
    except Exception:  # pragma: no cover
        return DefaultAzureCredential()


def _activity_to_dicts(activity: Any) -> list[dict[str, Any]]:
    """Normalize KB retrieval activity objects to plain dicts (SDK ``as_dict``)."""
    records: list[dict[str, Any]] = []
    for item in activity or []:
        if isinstance(item, dict):
            records.append(item)
        elif hasattr(item, "as_dict"):
            records.append(item.as_dict())
    return records


_tracing_provider_cls: Any = None


def _tracing_provider_class() -> Any:
    """Build (once) a context-provider subclass that records KB query-planning
    activity, which the base provider retrieves but does not expose."""
    global _tracing_provider_cls
    if _tracing_provider_cls is not None:
        return _tracing_provider_cls
    from agent_framework_azure_ai_search import AzureAISearchContextProvider

    class _TracingAzureAISearchContextProvider(AzureAISearchContextProvider):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.last_activity: list[dict[str, Any]] = []

        async def _agentic_search(self, messages: Any) -> Any:
            self.last_activity = []
            await self._ensure_knowledge_base()
            client = self._retrieval_client
            if client is not None and not getattr(client, "_hr_activity_wrapped", False):
                original_retrieve = client.retrieve

                async def _traced_retrieve(*args: Any, **kwargs: Any) -> Any:
                    response = await original_retrieve(*args, **kwargs)
                    self.last_activity = _activity_to_dicts(
                        getattr(response, "activity", None)
                    )
                    return response

                client.retrieve = _traced_retrieve  # type: ignore[method-assign]
                client._hr_activity_wrapped = True
            return await super()._agentic_search(messages)

    _tracing_provider_cls = _TracingAzureAISearchContextProvider
    return _tracing_provider_cls


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
    provider_cls = _tracing_provider_class()

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
        logger.info(
            "Agent Framework RAG: agentic retrieval over knowledge base '%s'",
            search_cfg.knowledge_base_name,
        )
        return provider_cls(
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
    return provider_cls(
        mode="semantic",
        index_name=index_name or search_cfg.index_name,
        semantic_configuration_name=search_cfg.semantic_configuration,
        **common,
    )
