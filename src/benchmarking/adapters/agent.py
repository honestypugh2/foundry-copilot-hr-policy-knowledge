"""Adapters for actual Foundry and Agent Framework answer call boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, Literal

from src.benchmarking.adapters.base import InvocationResult
from src.benchmarking.models import (
    AvailabilityReason,
    MetricValue,
    RetrievalReference,
)

AgentCallable = Callable[[str], Awaitable[dict[str, Any]]]


class AgentAnswerAdapter:
    """Measure the actual agent invocation without diagnostic re-retrieval."""

    def __init__(
        self,
        answer: AgentCallable,
        *,
        pattern: Literal["B", "Hosted"],
        invocation_path: str,
    ) -> None:
        self._answer = answer
        self._pattern = pattern
        self._invocation_path = invocation_path

    @property
    def pattern(self) -> Literal["B", "Hosted"]:
        return self._pattern

    @property
    def invocation_path(self) -> str:
        return self._invocation_path

    async def invoke(self, query: str, top: int) -> InvocationResult:
        del top
        started = perf_counter()
        payload = await self._answer(query)
        elapsed_ms = (perf_counter() - started) * 1000
        citations = payload.get("citations") or []
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
            )
            for citation in citations
        ]
        metrics = {
            "client_wall_time_ms": MetricValue(
                value=elapsed_ms, unit="ms", measurement_type="measured"
            ),
            "service_elapsed_time_ms": MetricValue(
                unit="ms",
                measurement_type="unavailable",
                unavailable_reason=AvailabilityReason.NOT_EXPOSED_BY_MCP,
            ),
        }
        usage = payload.get("usage") or {}
        for source_key, metric_key in (
            ("input_tokens", "input_tokens"),
            ("cached_input_tokens", "cached_input_tokens"),
            ("output_tokens", "output_tokens"),
            ("reasoning_tokens", "reasoning_tokens"),
        ):
            value = usage.get(source_key)
            if value is not None:
                metrics[metric_key] = MetricValue(
                    value=int(value), unit="tokens", measurement_type="service_reported"
                )
        timings = payload.get("timings") or {}
        for metric_key in ("ttft_ms", "ttlt_ms", "stream_duration_ms"):
            value = timings.get(metric_key)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value >= 0
            ):
                metrics[metric_key] = MetricValue(
                    value=float(value), unit="ms", measurement_type="measured"
                )
        return InvocationResult(
            status=payload.get("status", "success"),
            error_classification=payload.get("error_classification"),
            answer=str(payload.get("answer") or ""),
            references=references,
            metrics=metrics,
            trace_id=payload.get("trace_id"),
            response_id=payload.get("response_id"),
            conversation_id=payload.get("conversation_id"),
            raw_metadata={
                "stream_timing_boundary": payload.get("stream_timing_boundary")
            }
            if payload.get("stream_timing_boundary")
            else {},
        )


class FoundryAgentAdapter(AgentAnswerAdapter):
    def __init__(self, answer: AgentCallable) -> None:
        super().__init__(
            answer,
            pattern="B",
            invocation_path="foundry_responses_agent_mcp",
        )

    @property
    def pattern(self) -> Literal["B"]:
        return "B"


class HostedAgentAdapter(AgentAnswerAdapter):
    def __init__(self, answer: AgentCallable) -> None:
        super().__init__(
            answer,
            pattern="Hosted",
            invocation_path="agent_framework_hosted",
        )

    @property
    def pattern(self) -> Literal["Hosted"]:
        return "Hosted"


class AgentFrameworkAdapter(AgentAnswerAdapter):
    """Measure the local Agent Framework path for one declared RAG mode."""

    def __init__(self, answer: AgentCallable, retrieval_mode: str) -> None:
        super().__init__(
            answer,
            pattern="Hosted",
            invocation_path=f"agent_framework_local:{retrieval_mode}",
        )

    @property
    def pattern(self) -> Literal["Hosted"]:
        return "Hosted"