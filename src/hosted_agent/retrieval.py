"""Self-contained retrieval helpers for the Foundry Hosted Agent.

This mirrors the classic/agentic context-provider logic in
``src/search/agentic_context_provider.py`` but has **no dependency on the repo
``src`` package**, because the hosted agent container packages only the
``src/hosted_agent`` directory (``COPY . ./`` in the Dockerfile). All
configuration is read from the environment variables declared for the agent in
``azure.yaml``.

Keep this in sync with ``src/search/agentic_context_provider.py``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, cast

logger = logging.getLogger(__name__)

RETRIEVAL_MODE_TOOL = "tool"
RETRIEVAL_MODE_CONTEXT_SEMANTIC = "context-semantic"
RETRIEVAL_MODE_CONTEXT_AGENTIC = "context-agentic"

_RETRIEVAL_MODE_ALIASES = {
    RETRIEVAL_MODE_TOOL: RETRIEVAL_MODE_TOOL,
    RETRIEVAL_MODE_CONTEXT_SEMANTIC: RETRIEVAL_MODE_CONTEXT_SEMANTIC,
    RETRIEVAL_MODE_CONTEXT_AGENTIC: RETRIEVAL_MODE_CONTEXT_AGENTIC,
    "semantic": RETRIEVAL_MODE_CONTEXT_SEMANTIC,
    "agentic": RETRIEVAL_MODE_CONTEXT_AGENTIC,
}

_CONTEXT_MODES = frozenset(
    {
        RETRIEVAL_MODE_CONTEXT_SEMANTIC,
        RETRIEVAL_MODE_CONTEXT_AGENTIC,
        "semantic",
        "agentic",
    }
)

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
    from azure.identity import DefaultAzureCredential

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

    Configuration is read from the environment variables declared for the hosted
    agent in ``azure.yaml`` (no dependency on the repo ``src`` package).
    """
    provider_cls = _tracing_provider_class()

    endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if not endpoint:
        raise ValueError(
            "AZURE_SEARCH_ENDPOINT is required to build the search context provider."
        )

    resolved_top_k = top_k or int(os.getenv("AI_SEARCH_TOP_K", "5"))
    key = api_key if (api_key and not api_key.startswith("your_")) else None
    common: dict[str, Any] = {"endpoint": endpoint, "top_k": resolved_top_k}
    if key:
        common["api_key"] = key
    else:
        common["credential"] = _resolve_credential()

    if mode.lower().endswith("agentic"):
        knowledge_base_name = os.getenv("AZURE_SEARCH_KNOWLEDGE_BASE_NAME", "")
        if not knowledge_base_name:
            raise ValueError(
                "AZURE_SEARCH_KNOWLEDGE_BASE_NAME is required for agentic retrieval."
            )
        output_mode = _OUTPUT_MODE_MAP.get(
            os.getenv("AZURE_SEARCH_KB_OUTPUT_MODE", "EXTRACTIVE").upper(),
            "extractive_data",
        )
        effort = os.getenv("AZURE_SEARCH_KB_REASONING_EFFORT", "medium").lower()
        if effort not in _VALID_EFFORTS:
            effort = "medium"
        logger.info(
            "Hosted RAG: agentic retrieval over knowledge base '%s'",
            knowledge_base_name,
        )
        return provider_cls(
            mode="agentic",
            knowledge_base_name=knowledge_base_name,
            knowledge_base_output_mode=cast(Any, output_mode),
            retrieval_reasoning_effort=cast(Any, effort),
            **common,
        )

    resolved_index = index_name or os.getenv("AZURE_SEARCH_INDEX_NAME", "")
    semantic_configuration = os.getenv("AI_SEARCH_SEMANTIC_CONFIG", "hr-semantic-config")
    logger.info(
        "Hosted RAG: classic (semantic) search over index '%s'", resolved_index
    )
    return provider_cls(
        mode="semantic",
        index_name=resolved_index,
        semantic_configuration_name=semantic_configuration,
        **common,
    )
