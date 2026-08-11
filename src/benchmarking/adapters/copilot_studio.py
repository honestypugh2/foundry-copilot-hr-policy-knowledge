"""Copilot Studio end-to-end benchmark adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import re
from time import perf_counter
from typing import Any, Literal

from src.benchmarking.adapters.base import InvocationResult
from src.benchmarking.models import (
    ActivityRecord,
    AvailabilityReason,
    MetricValue,
    RetrievalReference,
)

CopilotCallable = Callable[[str], Awaitable[dict[str, Any]]]
Pattern = Literal["A", "A2", "B", "C", "Hosted"]
POLICY_CITATION = re.compile(r"\[Policy\s+(?P<number>\d{5})(?:\s+-\s+(?P<title>[^\]]+))?\]")


def _citation_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    citations = list(payload.get("citations") or [])
    for activity in payload.get("activities") or []:
        channel_data = activity.get("channelData") or {}
        citations.extend(channel_data.get("citations") or [])
        citations.extend(
            entity
            for entity in activity.get("entities") or []
            if str(entity.get("type", "")).lower() == "citation"
        )
    return citations


class CopilotStudioAdapter:
    """Measure a published Copilot Studio agent at its Direct Line boundary."""

    def __init__(
        self,
        ask: CopilotCallable,
        *,
        pattern: Pattern,
        route_template: str = "{query}",
    ) -> None:
        if "{query}" not in route_template:
            raise ValueError("route_template must contain {query}")
        self._ask = ask
        self._pattern: Pattern = pattern
        self._route_template = route_template

    @property
    def pattern(self) -> Pattern:
        return self._pattern

    @property
    def invocation_path(self) -> str:
        return f"copilot_studio_direct_line:{self.pattern}"

    async def invoke(self, query: str, top: int) -> InvocationResult:
        del top
        routed_query = self._route_template.format(pattern=self.pattern, query=query)
        started = perf_counter()
        payload = await self._ask(routed_query)
        elapsed_ms = (perf_counter() - started) * 1000

        answer = str(payload.get("answer") or "")
        timed_out = bool(payload.get("timed_out"))
        citations = _citation_payloads(payload)
        references = [
            RetrievalReference(
                source_id=str(
                    citation.get("source_id")
                    or citation.get("policy_number")
                    or citation.get("id")
                    or "unknown"
                ),
                policy_number=str(citation.get("policy_number") or "") or None,
                title=str(citation.get("title") or "") or None,
                source_url=str(citation.get("source_url") or citation.get("url") or "")
                or None,
            )
            for citation in citations
        ]
        if not references:
            references = [
                RetrievalReference(
                    source_id=match.group("number"),
                    policy_number=match.group("number"),
                    title=match.group("title"),
                )
                for match in POLICY_CITATION.finditer(answer)
            ]
        return InvocationResult(
            status="timeout" if timed_out else "success",
            error_classification=(
                "CopilotStudioResponseTimeout" if timed_out else None
            ),
            answer=answer,
            references=references,
            activity=[
                ActivityRecord.model_validate(activity)
                for activity in payload.get("activities") or []
            ],
            metrics={
                "client_wall_time_ms": MetricValue(
                    value=elapsed_ms,
                    unit="ms",
                    measurement_type="measured",
                ),
                "service_elapsed_time_ms": MetricValue(
                    unit="ms",
                    measurement_type="unavailable",
                    unavailable_reason=AvailabilityReason.NOT_EXPOSED,
                ),
            },
            conversation_id=payload.get("conversation_id"),
            response_id=payload.get("activity_id"),
            raw_metadata={
                "measurement_boundary": "copilot_studio_direct_line",
                "routed_query": routed_query,
            },
        )