"""Adapter for the repository's direct classic Search path."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal

from opentelemetry import trace

from src.benchmarking.adapters.base import InvocationResult
from src.benchmarking.models import MetricValue, RetrievalReference

SearchCallable = Callable[[str, int], list[dict[str, Any]]]
_TRACER = trace.get_tracer(__name__)


class DirectSearchAdapter:
    """Measure a direct Search call without changing production routing."""

    pattern: Literal["A"] = "A"
    invocation_path: Literal["direct_search_sdk"] = "direct_search_sdk"

    def __init__(self, search: SearchCallable) -> None:
        self._search = search

    async def invoke(self, query: str, top: int) -> InvocationResult:
        with _TRACER.start_as_current_span("azure_search.query") as span:
            span.set_attribute("app.benchmark.invocation.path", self.invocation_path)
            span.set_attribute("azure.search.top", top)
            started = perf_counter()
            hits = self._search(query, top)
            elapsed_ms = (perf_counter() - started) * 1000
            span.set_attribute("azure.search.result.count", len(hits))
            span.set_attribute("azure.search.client_wall_time_ms", elapsed_ms)
        references = [
            RetrievalReference(
                source_id=str(
                    hit.get("source_id")
                    or hit.get("policy_number")
                    or hit.get("id")
                    or "unknown"
                ),
                policy_number=str(hit.get("policy_number") or "") or None,
                title=str(hit.get("parentTitle") or hit.get("title") or "") or None,
                score=float(hit["score"]) if hit.get("score") is not None else None,
            )
            for hit in hits
        ]
        return InvocationResult(
            references=references,
            metrics={
                "client_wall_time_ms": MetricValue(
                    value=elapsed_ms,
                    unit="ms",
                    measurement_type="measured",
                )
            },
        )