from __future__ import annotations

from opentelemetry import baggage, context

from src.observability.benchmark_correlation import (
    BenchmarkCorrelationSpanProcessor,
    benchmark_correlation_context,
)


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, str] = {}

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value


def test_benchmark_correlation_propagates_allowlisted_values_and_cleans_up():
    processor = BenchmarkCorrelationSpanProcessor()
    span = _FakeSpan()

    with benchmark_correlation_context(
        {
            "experiment.id": "exp-1",
            "pattern": "Hosted",
            "case.id": "case-1",
            "session.id": "session-1",
            "query": "must-not-be-recorded",
        }
    ):
        current = context.get_current()
        processor.on_start(span, current)
        assert baggage.get_baggage("app.benchmark.experiment.id") == "exp-1"

    assert span.attributes == {
        "app.benchmark.experiment.id": "exp-1",
        "app.benchmark.pattern": "Hosted",
        "app.benchmark.case.id": "case-1",
        "app.benchmark.session.id": "session-1",
    }
    assert baggage.get_baggage("app.benchmark.experiment.id") is None
    assert "app.benchmark.query" not in span.attributes