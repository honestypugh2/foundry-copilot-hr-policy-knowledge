"""Command-line runner for controlled benchmark experiments."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.benchmarking.adapters.copilot_studio import CopilotStudioAdapter
from src.benchmarking.adapters.direct_search import DirectSearchAdapter
from src.benchmarking.aggregation import aggregate_results
from src.benchmarking.models import BenchmarkCase, ExperimentManifest, PricingProfile
from src.benchmarking.reporting import (
    write_jsonl,
    write_report_json,
    write_report_markdown,
)
from src.observability import enable_tracing, flush_tracing
from src.benchmarking.runner import BenchmarkRunner


def _verify_live_identity() -> None:
    from src.config.azure_identity import verify_azure_cli_identity

    verify_azure_cli_identity(
        expected_tenant_id=os.environ.get("EXPECTED_AZURE_TENANT_ID", ""),
        expected_subscription_id=os.environ.get(
            "EXPECTED_AZURE_SUBSCRIPTION_ID", ""
        ),
        expected_principal_id=os.environ.get("EXPECTED_AZURE_PRINCIPAL_ID", ""),
    )


def _load_model_list(path: Path, model_type: type[Any]) -> list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [model_type.model_validate(item) for item in payload]


def _fixture_search(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Fixture responses must be a JSON object keyed by query")

    def search(query: str, top: int) -> list[dict[str, Any]]:
        response = payload.get(query, [])
        if not isinstance(response, list):
            raise ValueError(f"Fixture response for {query!r} must be a JSON array")
        return response[:top]

    return search


def _build_adapter(
    manifest: ExperimentManifest,
    fixture_responses: Path | None,
    *,
    copilot_studio: bool = False,
    route_template: str = "{query}",
    copilot_environment_id: str | None = None,
    copilot_agent_schema: str | None = None,
    copilot_token_endpoint: str | None = None,
    agent_framework: bool = False,
):
    if agent_framework:
        if manifest.pattern != "Hosted":
            raise ValueError("--agent-framework requires pattern 'Hosted'")
        from src.agents.hr_policy_agent_af import HRPolicyAgent
        from src.benchmarking.adapters.agent import AgentFrameworkAdapter
        from src.search.agentic_context_provider import normalize_retrieval_mode

        retrieval_mode = normalize_retrieval_mode(manifest.retrieval_mode)
        agent = HRPolicyAgent(retrieval_mode=retrieval_mode)
        return AgentFrameworkAdapter(agent.answer_question_async, retrieval_mode)
    if copilot_studio:
        from src.copilot_studio.service import CopilotStudioService

        service = CopilotStudioService(
            environment_id=copilot_environment_id,
            agent_schema=copilot_agent_schema,
            token_endpoint=copilot_token_endpoint,
        )
        if not service.is_configured:
            raise ValueError(
                "Copilot Studio requires COPILOT_STUDIO_ENVIRONMENT_ID and "
                "COPILOT_STUDIO_AGENT_SCHEMA"
            )
        return CopilotStudioAdapter(
            service.ask,
            pattern=manifest.pattern,
            route_template=route_template,
        )
    if manifest.pattern != "A":
        raise ValueError(
            "The CLI currently automates Pattern A only; use normalized imports "
            "for externally driven patterns"
        )
    if fixture_responses is not None:
        return DirectSearchAdapter(_fixture_search(fixture_responses))

    from src.search.integrated_vectorization_search import (
        IntegratedVectorizationSearchService,
    )

    service = IntegratedVectorizationSearchService()
    return DirectSearchAdapter(service.search)


async def run_experiment(
    manifest: ExperimentManifest,
    cases: list[BenchmarkCase],
    output_dir: Path,
    *,
    fixture_responses: Path | None = None,
    copilot_studio: bool = False,
    route_template: str = "{query}",
    copilot_environment_id: str | None = None,
    copilot_agent_schema: str | None = None,
    copilot_token_endpoint: str | None = None,
    agent_framework: bool = False,
    pricing_profile: PricingProfile | None = None,
) -> None:
    adapter = _build_adapter(
        manifest,
        fixture_responses,
        copilot_studio=copilot_studio,
        route_template=route_template,
        copilot_environment_id=copilot_environment_id,
        copilot_agent_schema=copilot_agent_schema,
        copilot_token_endpoint=copilot_token_endpoint,
        agent_framework=agent_framework,
    )
    runner = BenchmarkRunner(manifest, adapter, pricing_profile)

    for _ in range(manifest.warmup_count):
        for case in cases:
            await adapter.invoke(case.query, manifest.top)

    results = []
    for _ in range(manifest.measured_repetitions):
        results.extend(await runner.run(cases))

    report = aggregate_results(results)
    report.provenance.update(
        {
            "manifest_schema_version": manifest.schema_version,
            "fixture_mode": fixture_responses is not None,
            "measurement_boundary": (
                "copilot_studio_direct_line" if copilot_studio else adapter.invocation_path
            ),
            "workload_type": "controlled_experiment",
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = manifest.experiment_id
    (output_dir / f"{stem}.manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    write_jsonl(output_dir / f"{stem}.results.jsonl", results)
    write_report_json(output_dir / f"{stem}.report.json", manifest, report)
    write_report_markdown(output_dir / f"{stem}.report.md", manifest, report)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)
    if os.getenv("ENABLE_TRACING", "false").lower() == "true":
        enable_tracing(instrument_ai_clients=False, sampling_ratio=1.0)
    parser = argparse.ArgumentParser(description="Run a controlled HR policy benchmark")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--pricing-profile",
        type=Path,
        help=(
            "Versioned pricing-profile JSON. Its name:version must match the "
            "manifest pricing_profile value."
        ),
    )
    parser.add_argument(
        "--fixture-responses",
        type=Path,
        help="Synthetic query-to-results JSON for credential-free contract testing",
    )
    parser.add_argument(
        "--copilot-studio",
        action="store_true",
        help="Run the manifest pattern end to end through the configured Copilot Studio agent",
    )
    parser.add_argument(
        "--agent-framework",
        action="store_true",
        help="Run a Hosted manifest through the local Agent Framework path",
    )
    parser.add_argument(
        "--route-template",
        default="{query}",
        help="Optional Copilot routing prompt containing {query}; real per-pattern agents should use the default",
    )
    parser.add_argument(
        "--copilot-environment-id",
        help="Power Platform environment ID for this agent (overrides .env)",
    )
    parser.add_argument(
        "--copilot-agent-schema",
        help="Schema name of the real Copilot Studio agent for this run (overrides .env)",
    )
    parser.add_argument(
        "--copilot-token-endpoint",
        help="Mobile-channel token endpoint for the real agent (overrides .env)",
    )
    args = parser.parse_args(argv)

    manifest = ExperimentManifest.model_validate_json(
        args.manifest.read_text(encoding="utf-8")
    )
    pricing_profile = None
    if args.pricing_profile is not None:
        pricing_profile = PricingProfile.model_validate_json(
            args.pricing_profile.read_text(encoding="utf-8")
        )
        profile_id = f"{pricing_profile.name}:{pricing_profile.version}"
        if manifest.pricing_profile != profile_id:
            parser.error(
                "The manifest pricing_profile must equal the loaded profile "
                f"identifier {profile_id!r}"
            )
    elif manifest.pricing_profile is not None:
        parser.error(
            "The manifest names a pricing_profile, so --pricing-profile is required"
        )
    cases = _load_model_list(args.cases, BenchmarkCase)
    if not cases:
        parser.error("The case dataset must not be empty")
    if args.fixture_responses is None:
        _verify_live_identity()
    try:
        asyncio.run(
            run_experiment(
                manifest,
                cases,
                args.output_dir,
                fixture_responses=args.fixture_responses,
                copilot_studio=args.copilot_studio,
                route_template=args.route_template,
                copilot_environment_id=args.copilot_environment_id,
                copilot_agent_schema=args.copilot_agent_schema,
                copilot_token_endpoint=args.copilot_token_endpoint,
                agent_framework=args.agent_framework,
                pricing_profile=pricing_profile,
            )
        )
    finally:
        if os.getenv("ENABLE_TRACING", "false").lower() == "true":
            flush_tracing()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())