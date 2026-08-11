"""Benchmark correlation for SDK-created OpenTelemetry spans."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from opentelemetry import baggage, context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

_ATTRIBUTE_PREFIX = "app.benchmark."
_ALLOWED_KEYS = frozenset(
    {
        "experiment.id",
        "pattern",
        "configuration.id",
        "run.id",
        "case.id",
        "session.id",
    }
)


def _attribute_name(key: str) -> str:
    return f"{_ATTRIBUTE_PREFIX}{key}"


@contextmanager
def benchmark_correlation_context(values: Mapping[str, str]) -> Iterator[None]:
    """Attach allowlisted benchmark values for child SDK spans."""
    current = context.get_current()
    updated = current
    for key, value in values.items():
        if key in _ALLOWED_KEYS and value:
            updated = baggage.set_baggage(_attribute_name(key), value, context=updated)
    token = context.attach(updated)
    try:
        yield
    finally:
        context.detach(token)


class BenchmarkCorrelationSpanProcessor(SpanProcessor):
    """Copy benchmark baggage to spans created by existing instrumentation."""

    def on_start(self, span: Span, parent_context: context.Context | None = None) -> None:
        for key, value in baggage.get_all(context=parent_context).items():
            if key.startswith(_ATTRIBUTE_PREFIX) and isinstance(value, str):
                span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True