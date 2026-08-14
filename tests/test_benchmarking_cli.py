from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.benchmarking.cli import _build_adapter, _validate_execution_boundary, main
from src.copilot_studio.service import CopilotStudioService
from scripts.generate_copilot_benchmark_manifests import generate
from tests.test_benchmarking_phase1 import _manifest


def test_cli_emits_versioned_offline_artifacts(tmp_path: Path):
    manifest = _manifest().model_copy(
        update={
            "experiment_id": "cli-smoke",
            "warmup_count": 1,
            "measured_repetitions": 2,
        }
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "pto-location",
                    "query": "Where is the PTO policy?",
                    "category": "document_location",
                    "expected_behavior": "retrieve",
                    "expected_source_ids": ["50010"],
                }
            ]
        ),
        encoding="utf-8",
    )
    fixtures_path = tmp_path / "fixtures.json"
    fixtures_path.write_text(
        json.dumps(
            {
                "Where is the PTO policy?": [
                    {
                        "policy_number": "50010",
                        "title": "Paid Time Off",
                        "score": 3.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"

    assert (
        main(
            [
                "--manifest",
                str(manifest_path),
                "--cases",
                str(cases_path),
                "--fixture-responses",
                str(fixtures_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    rows = [
        json.loads(line)
        for line in (output_dir / "cli-smoke.results.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 2
    assert all(row["local_metrics"]["recall_at_k"] == 1.0 for row in rows)
    aggregate = json.loads(
        (output_dir / "cli-smoke.report.json").read_text(encoding="utf-8")
    )["aggregate"]
    assert aggregate["provenance"]["fixture_mode"] is True
    assert aggregate["provenance"]["workload_type"] == "controlled_experiment"
    markdown = (output_dir / "cli-smoke.report.md").read_text(encoding="utf-8")
    assert "Controlled development experiment" in markdown
    assert "not Azure performance evidence" in markdown
    assert json.loads(
        (output_dir / "cli-smoke.manifest.json").read_text(encoding="utf-8")
    )["schema_version"] == "1.0"


def test_cli_rejects_pricing_profile_not_named_by_manifest(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(_manifest().model_dump_json(), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "pricing-check",
                    "query": "What is PTO?",
                    "category": "direct_fact",
                    "expected_behavior": "retrieve",
                    "expected_source_ids": ["50010"],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        main(
            [
                "--manifest",
                str(manifest_path),
                "--cases",
                str(cases_path),
                "--fixture-responses",
                str(tmp_path / "unused-fixtures.json"),
                "--pricing-profile",
                "experiments/pricing/azure-gpt-5-mini-global-standard-2025-08-01.json",
                "--output-dir",
                str(tmp_path / "reports"),
            ]
        )


def test_cli_rejects_unconfigured_copilot_studio(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.benchmarking.cli.load_dotenv", lambda **_: None)
    monkeypatch.setattr("src.benchmarking.cli._verify_live_identity", lambda: None)
    monkeypatch.delenv("COPILOT_STUDIO_ENVIRONMENT_ID", raising=False)
    monkeypatch.delenv("COPILOT_STUDIO_AGENT_SCHEMA", raising=False)
    manifest_path = tmp_path / "manifest.json"
    manifest = _manifest().model_copy(
        update={"invocation_path": "copilot_studio_direct_line:test-agent"}
    )
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "configured-check",
                    "query": "What is PTO?",
                    "category": "direct_fact",
                    "expected_behavior": "answer",
                    "expected_source_ids": ["50010"],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="COPILOT_STUDIO_ENVIRONMENT_ID"):
        main(
            [
                "--manifest",
                str(manifest_path),
                "--cases",
                str(cases_path),
                "--output-dir",
                str(tmp_path / "reports"),
                "--copilot-studio",
            ]
        )


def test_agent_framework_adapter_records_canonical_mode(monkeypatch):
    class FakeAgent:
        def __init__(self, *, retrieval_mode: str):
            self.retrieval_mode = retrieval_mode

        async def answer_question_async(self, query: str):
            return {"answer": query, "citations": []}

    monkeypatch.setattr(
        "src.agents.hr_policy_agent_af.HRPolicyAgent",
        FakeAgent,
    )
    manifest = _manifest().model_copy(
        update={"pattern": "Hosted", "retrieval_mode": "semantic"}
    )

    adapter = _build_adapter(manifest, None, agent_framework=True)

    assert adapter.pattern == "Hosted"
    assert adapter.invocation_path == "agent_framework_local:context-semantic"


def test_copilot_adapter_targets_explicit_real_agent(monkeypatch):
    monkeypatch.setenv("COPILOT_STUDIO_ENVIRONMENT_ID", "env-from-dotenv")
    monkeypatch.setenv("COPILOT_STUDIO_AGENT_SCHEMA", "agent-from-dotenv")
    monkeypatch.setenv("COPILOT_STUDIO_TOKEN_ENDPOINT", "https://old.example/token")

    adapter = _build_adapter(
        _manifest(),
        None,
        copilot_studio=True,
        copilot_environment_id="real-environment",
        copilot_agent_schema="cr4ba_askHrPatternA",
        copilot_token_endpoint="https://new.example/token",
    )

    service = CopilotStudioService(
        environment_id="real-environment",
        agent_schema="cr4ba_askHrPatternA",
        token_endpoint="https://new.example/token",
    )
    assert adapter.invocation_path == "copilot_studio_direct_line:A"
    assert service.environment_id == "real-environment"
    assert service.agent_schema == "cr4ba_askHrPatternA"
    assert service.token_endpoint_url == "https://new.example/token"


def test_execution_boundary_requires_matching_copilot_manifest_and_flag():
    direct_manifest = _manifest()
    copilot_manifest = direct_manifest.model_copy(
        update={"invocation_path": "copilot_studio_direct_line:Default_AskHRPolicyAgent"}
    )

    with pytest.raises(ValueError, match="same execution boundary"):
        _validate_execution_boundary(copilot_manifest, copilot_studio=False)
    with pytest.raises(ValueError, match="same execution boundary"):
        _validate_execution_boundary(direct_manifest, copilot_studio=True)

    _validate_execution_boundary(copilot_manifest, copilot_studio=True)
    _validate_execution_boundary(direct_manifest, copilot_studio=False)


def test_copilot_manifest_identifies_real_agent_and_model(tmp_path: Path):
    agent_source = tmp_path / "Ask HR Policy Agent - A"
    agent_source.mkdir()
    (agent_source / "agent.mcs.yml").write_text(
        "instructions: HR policy only\n", encoding="utf-8"
    )
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "case_id": "pto",
                    "query": "What is PTO?",
                    "category": "direct_fact",
                    "expected_behavior": "answer",
                    "expected_source_ids": ["50010"],
                }
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "manifests"

    generate(
        pattern="A",
        agent_name="Ask HR Policy Agent - A",
        agent_source=agent_source,
        dataset=dataset,
        output_dir=output_dir,
        corpus_fingerprint="corpus-v1",
        index_fingerprint="index-v1",
        repetitions=3,
        model_deployment="Claude Sonnet 4.6",
    )

    manifest = json.loads(
        (output_dir / "copilot-ask-hr-policy-agent-a.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["pattern"] == "A"
    assert manifest["model_deployment"] == "Claude Sonnet 4.6"
    assert manifest["invocation_path"] == (
        "copilot_studio_direct_line:Ask HR Policy Agent - A"
    )
    assert manifest["knowledge_source_settings"]["copilot_studio_agent"] == (
        "Ask HR Policy Agent - A"
    )
    assert manifest["configuration_version"]