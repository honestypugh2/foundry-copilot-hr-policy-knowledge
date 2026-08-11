from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from src.benchmarking.adapters import (
    CopilotStudioAdapter,
    DirectKnowledgeBaseAdapter,
    DirectSearchAdapter,
    FoundryAgentAdapter,
    HostedAgentAdapter,
    PatternCLookupAdapter,
    load_copilot_studio_results,
)
from src.benchmarking.models import BenchmarkCase
from src.benchmarking.runner import BenchmarkRunner
from tests.test_benchmarking_phase1 import _manifest


async def test_direct_search_adapter_emits_safe_search_span(monkeypatch):
    class FakeSpan:
        def __init__(self):
            self.attributes = {}

        def set_attribute(self, key, value):
            self.attributes[key] = value

    class FakeTracer:
        def __init__(self):
            self.span = FakeSpan()

        @contextmanager
        def start_as_current_span(self, name):
            assert name == "azure_search.query"
            yield self.span

    tracer = FakeTracer()
    clock = iter([0.0, 0.025])
    monkeypatch.setattr("src.benchmarking.adapters.direct_search._TRACER", tracer)
    monkeypatch.setattr(
        "src.benchmarking.adapters.direct_search.perf_counter",
        lambda: next(clock),
    )
    query = "private HR query"
    adapter = DirectSearchAdapter(
        lambda received_query, top: [
            {"policy_number": "50010", "title": "Paid Time Off"}
        ]
        if (received_query, top) == (query, 3)
        else []
    )

    result = await adapter.invoke(query, 3)

    assert result.references[0].source_id == "50010"
    assert tracer.span.attributes == {
        "app.benchmark.invocation.path": "direct_search_sdk",
        "azure.search.top": 3,
        "azure.search.result.count": 1,
        "azure.search.client_wall_time_ms": 25.0,
    }
    assert query not in str(tracer.span.attributes)


@pytest.mark.parametrize(
    ("adapter_type", "pattern"),
    [(FoundryAgentAdapter, "B"), (HostedAgentAdapter, "Hosted")],
)
async def test_agent_adapters_measure_actual_invocation_without_second_retrieval(
    adapter_type, pattern, monkeypatch
):
    calls = 0

    async def answer(query: str):
        nonlocal calls
        calls += 1
        assert query == "What is PTO?"
        return {
            "answer": "See [Policy 50010 - Paid Time Off].",
            "citations": [{"policy_number": "50010", "title": "Paid Time Off"}],
            "usage": {
                "input_tokens": 12,
                "cached_input_tokens": 4,
                "output_tokens": 8,
            },
            "timings": {
                "ttft_ms": 10.0,
                "ttlt_ms": 20.0,
                "stream_duration_ms": 10.0,
            },
            "stream_timing_boundary": "agent.run start to stream completion",
            "response_id": "response-1",
        }

    clock = iter([0.0, 0.025])
    monkeypatch.setattr("src.benchmarking.adapters.agent.perf_counter", lambda: next(clock))
    manifest = _manifest().model_copy(update={"pattern": pattern})
    runner = BenchmarkRunner(manifest, adapter_type(answer))
    results = await runner.run(
        [
            BenchmarkCase(
                case_id="pto",
                query="What is PTO?",
                category="direct_fact",
                expected_behavior="answer",
                expected_source_ids=["50010"],
            )
        ]
    )

    assert calls == 1
    assert results[0].pattern == pattern
    assert results[0].service_elapsed_time_ms.unavailable_reason == "not_exposed_by_mcp"
    assert results[0].cached_input_tokens.value == 4
    assert results[0].cached_input_tokens.measurement_type == "service_reported"
    assert results[0].output_tokens.value == 8
    assert results[0].ttft_ms.value == 10
    assert results[0].ttlt_ms.value == 20
    assert results[0].stream_duration_ms.value == 10
    assert results[0].response_id == "response-1"


async def test_pattern_c_records_deterministic_source_and_no_model_tokens(monkeypatch):
    clock = iter([0.0, 0.004])
    monkeypatch.setattr("src.benchmarking.adapters.pattern_c.perf_counter", lambda: next(clock))
    adapter = PatternCLookupAdapter(
        lambda query, top: [
            {
                "policy_number": "50010",
                "parent_title": "Paid Time Off",
                "blob_url": "https://example.test/pto.docx",
                "score": 2.5,
            }
        ]
    )
    result = (await BenchmarkRunner(
        _manifest().model_copy(update={"pattern": "C"}), adapter
    ).run([
        BenchmarkCase(
            case_id="locate-pto",
            query="Where is the PTO policy?",
            category="document_location",
            expected_behavior="locate",
            expected_source_ids=["50010"],
        )
    ]))[0]

    assert result.references[0].source_url == "https://example.test/pto.docx"
    assert result.input_tokens.unavailable_reason == "not_applicable"
    assert result.local_metrics["exact_source_path_present"] is True


async def test_direct_knowledge_base_preserves_official_envelope(monkeypatch):
    calls = 0

    async def retrieve(query: str, top: int):
        nonlocal calls
        calls += 1
        assert (query, top) == ("Compare policies", 3)
        return {
            "response": "Synthetic grounded response",
            "activity": [
                {"type": "searchIndex", "elapsedMs": 12, "futureField": True},
                {"type": "futureActivity", "id": "new"},
            ],
            "references": [
                {
                    "id": "SYNTH-POLICY-ALPHA",
                    "source_data": {
                        "policy_number": "SYNTH-POLICY-ALPHA",
                        "title": "Synthetic Leave Policy",
                        "metadata_storage_path": "https://example.test/alpha",
                    },
                }
            ],
            "responseId": "kb-response-1",
        }

    clock = iter([0.0, 0.018])
    monkeypatch.setattr(
        "src.benchmarking.adapters.knowledge_base.perf_counter", lambda: next(clock)
    )
    result = (
        await BenchmarkRunner(
            _manifest().model_copy(update={"pattern": "A2"}),
            DirectKnowledgeBaseAdapter(retrieve),
        ).run(
            [
                BenchmarkCase(
                    case_id="compare",
                    query="Compare policies",
                    category="multi_policy_synthesis",
                    expected_behavior="cite",
                    expected_source_ids=["SYNTH-POLICY-ALPHA"],
                )
            ]
        )
    )[0]

    assert calls == 1
    assert result.client_wall_time_ms.value == pytest.approx(18)
    assert result.response_id == "kb-response-1"
    assert result.activity[0].model_dump(by_alias=True)["futureField"] is True
    assert result.activity[1].type == "futureActivity"
    assert result.references[0].source_url == "https://example.test/alpha"
    assert result.service_elapsed_time_ms.unavailable_reason == "not_exposed"


async def test_copilot_import_requires_explicit_external_boundary(tmp_path):
    agent = FoundryAgentAdapter(lambda query: None)  # type: ignore[arg-type]
    result = (await BenchmarkRunner(
        _manifest().model_copy(update={"pattern": "B"}), agent
    ).run([]))
    assert result == []

    path = tmp_path / "copilot.jsonl"
    path.write_text(json.dumps({"measurement_boundary": "browser", "result": {}}) + "\n")
    with pytest.raises(ValueError, match="Copilot measurement boundary"):
        load_copilot_studio_results(path)


async def test_copilot_studio_adapter_routes_and_measures_external_boundary(monkeypatch):
    received_query = ""

    async def ask(query: str):
        nonlocal received_query
        received_query = query
        return {
            "answer": "See the Paid Time Off policy. [Policy 50010 - Paid Time Off]",
            "activities": [
                {
                    "type": "message",
                    "channelData": {
                        "citations": [
                            {
                                "policy_number": "50010",
                                "title": "Paid Time Off",
                                "url": "https://example.test/pto",
                            }
                        ]
                    },
                }
            ],
            "conversation_id": "conversation-1",
            "activity_id": "activity-1",
        }

    clock = iter([0.0, 0.125])
    monkeypatch.setattr(
        "src.benchmarking.adapters.copilot_studio.perf_counter", lambda: next(clock)
    )
    adapter = CopilotStudioAdapter(
        ask,
        pattern="A2",
        route_template="/benchmark {pattern} {query}",
    )

    result = await adapter.invoke("What is PTO?", top=5)

    assert received_query == "/benchmark A2 What is PTO?"
    assert adapter.invocation_path == "copilot_studio_direct_line:A2"
    assert result.metrics["client_wall_time_ms"].value == pytest.approx(125)
    assert result.metrics["service_elapsed_time_ms"].unavailable_reason == "not_exposed"
    assert result.references[0].source_id == "50010"
    assert result.activity[0].model_dump()["channelData"]["citations"][0]["url"]
    assert result.conversation_id == "conversation-1"


async def test_copilot_studio_adapter_uses_explicit_policy_citation_fallback():
    async def ask(query: str):
        return {"answer": "Use the leave rules. [Policy 50020 - Part-time PTO]"}

    result = await CopilotStudioAdapter(ask, pattern="A").invoke("PTO?", top=5)

    assert result.references[0].source_id == "50020"
    assert result.references[0].title == "Part-time PTO"


async def test_copilot_studio_adapter_classifies_response_timeout():
    async def ask(query: str):
        return {
            "answer": "",
            "activities": [],
            "timed_out": True,
            "conversation_id": "conversation-timeout",
        }

    result = await CopilotStudioAdapter(ask, pattern="B").invoke("PTO?", top=5)

    assert result.status == "timeout"
    assert result.error_classification == "CopilotStudioResponseTimeout"
    assert result.conversation_id == "conversation-timeout"