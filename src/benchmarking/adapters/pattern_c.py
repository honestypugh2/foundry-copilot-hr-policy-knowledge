"""Adapter for deterministic Pattern C document lookup."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal

from src.benchmarking.adapters.base import InvocationResult
from src.benchmarking.models import (
    AvailabilityReason,
    MetricValue,
    RetrievalReference,
)

LookupCallable = Callable[[str, int], list[dict[str, Any]]]


class PatternCLookupAdapter:
    pattern: Literal["C"] = "C"
    invocation_path: Literal["deterministic_lookup"] = "deterministic_lookup"

    def __init__(self, lookup: LookupCallable) -> None:
        self._lookup = lookup

    async def invoke(self, query: str, top: int) -> InvocationResult:
        started = perf_counter()
        documents = self._lookup(query, top)
        elapsed_ms = (perf_counter() - started) * 1000
        references = [
            RetrievalReference(
                source_id=str(
                    document.get("source_id")
                    or document.get("policy_number")
                    or document.get("blob_url")
                    or "unknown"
                ),
                policy_number=str(document.get("policy_number") or "") or None,
                title=str(
                    document.get("parent_title")
                    or document.get("parentTitle")
                    or document.get("title")
                    or ""
                )
                or None,
                score=(
                    float(document["score"])
                    if document.get("score") is not None
                    else None
                ),
                source_url=str(document.get("blob_url") or "") or None,
            )
            for document in documents
        ]
        unavailable = MetricValue(
            unit="tokens",
            measurement_type="unavailable",
            unavailable_reason=AvailabilityReason.NOT_APPLICABLE,
        )
        return InvocationResult(
            references=references,
            metrics={
                "client_wall_time_ms": MetricValue(
                    value=elapsed_ms, unit="ms", measurement_type="measured"
                ),
                "input_tokens": unavailable,
                "output_tokens": unavailable,
            },
            local_metrics={
                "exact_source_path_present": all(
                    bool(document.get("blob_url") or document.get("metadata_storage_path"))
                    for document in documents
                )
            },
        )