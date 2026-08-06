"""Direct Azure AI Search Knowledge Base benchmark adapter."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, Literal

from src.benchmarking.activity import parse_activity
from src.benchmarking.adapters.base import InvocationResult
from src.benchmarking.models import MetricValue, RetrievalReference

RetrieveCallable = Callable[[str, int], dict[str, Any] | Awaitable[dict[str, Any]]]


def _reference(item: dict[str, Any]) -> RetrievalReference:
    source_data = item.get("source_data") or item.get("sourceData") or {}
    source_id = str(
        item.get("source_id")
        or item.get("id")
        or source_data.get("policy_number")
        or source_data.get("metadata_storage_path")
        or "unknown"
    )
    return RetrievalReference(
        source_id=source_id,
        policy_number=source_data.get("policy_number") or item.get("policy_number"),
        title=(
            source_data.get("title")
            or source_data.get("parent_title")
            or item.get("title")
        ),
        score=item.get("score"),
        source_url=(
            source_data.get("blob_url")
            or source_data.get("metadata_storage_path")
            or item.get("source_url")
        ),
    )


class DirectKnowledgeBaseAdapter:
    """Normalize one direct GA Knowledge Base retrieval invocation."""

    pattern: Literal["A2"] = "A2"
    invocation_path: Literal["direct_knowledge_base_retrieve"] = (
        "direct_knowledge_base_retrieve"
    )

    def __init__(self, retrieve: RetrieveCallable) -> None:
        self._retrieve = retrieve

    async def invoke(self, query: str, top: int) -> InvocationResult:
        started = perf_counter()
        payload = self._retrieve(query, top)
        if inspect.isawaitable(payload):
            payload = await payload
        elapsed_ms = (perf_counter() - started) * 1000
        return InvocationResult(
            answer=str(payload.get("response") or ""),
            references=[
                _reference(item)
                for item in payload.get("references", [])
                if isinstance(item, dict)
            ],
            activity=parse_activity(payload.get("activity")),
            metrics={
                "client_wall_time_ms": MetricValue(
                    value=elapsed_ms,
                    unit="ms",
                    measurement_type="measured",
                )
            },
            response_id=payload.get("response_id") or payload.get("responseId"),
        )