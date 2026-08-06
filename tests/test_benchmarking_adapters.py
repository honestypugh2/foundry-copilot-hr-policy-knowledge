from __future__ import annotations

import json

import pytest

from src.benchmarking.adapters import (
    DirectKnowledgeBaseAdapter,
    FoundryAgentAdapter,
    HostedAgentAdapter,
    PatternCLookupAdapter,
    load_copilot_studio_results,
)
from src.benchmarking.models import BenchmarkCase
from src.benchmarking.runner import BenchmarkRunner
from tests.test_benchmarking_phase1 import _manifest


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
            "usage": {"input_tokens": 12, "output_tokens": 8},
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
    assert results[0].output_tokens.value == 8
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