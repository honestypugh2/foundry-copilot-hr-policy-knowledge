from __future__ import annotations

from pathlib import Path


KQL_ROOT = Path("experiments/kql")


def test_kql_templates_are_bounded_and_do_not_project_sensitive_content():
    templates = sorted(KQL_ROOT.glob("*.kql"))
    assert {path.name for path in templates} == {
        "benchmark_failures.kql",
        "benchmark_latency_percentiles.kql",
        "evaluation_correlation.kql",
        "search_capacity.kql",
        "token_latency_correlation.kql",
    }
    forbidden = {
        "gen_ai.input.messages",
        "gen_ai.output.messages",
        "gen_ai.tool.call.arguments",
        "gen_ai.tool.call.result",
    }
    for path in templates:
        query = path.read_text(encoding="utf-8")
        assert "ago(timeRange)" in query
        assert not forbidden.intersection(query)


def test_trace_templates_expose_benchmark_correlation_without_metric_reconstruction():
    trace_queries = "\n".join(
        path.read_text(encoding="utf-8")
        for path in KQL_ROOT.glob("*.kql")
        if path.name != "search_capacity.kql"
    )
    assert "app.benchmark.experiment.id" in trace_queries
    assert "app.benchmark.pattern" in trace_queries
    assert "orchestration overhead" not in trace_queries.lower()
    assert "activity_total" not in trace_queries