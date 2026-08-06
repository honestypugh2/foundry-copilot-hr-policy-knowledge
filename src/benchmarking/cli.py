"""Command-line runner for controlled benchmark experiments."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from src.benchmarking.adapters.direct_search import DirectSearchAdapter
from src.benchmarking.aggregation import aggregate_results
from src.benchmarking.models import BenchmarkCase, ExperimentManifest
from src.benchmarking.reporting import (
    write_jsonl,
    write_report_json,
    write_report_markdown,
)
from src.benchmarking.runner import BenchmarkRunner


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


def _build_adapter(manifest: ExperimentManifest, fixture_responses: Path | None):
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
) -> None:
    adapter = _build_adapter(manifest, fixture_responses)
    runner = BenchmarkRunner(manifest, adapter)

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
    parser = argparse.ArgumentParser(description="Run a controlled HR policy benchmark")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--fixture-responses",
        type=Path,
        help="Synthetic query-to-results JSON for credential-free contract testing",
    )
    args = parser.parse_args(argv)

    manifest = ExperimentManifest.model_validate_json(
        args.manifest.read_text(encoding="utf-8")
    )
    cases = _load_model_list(args.cases, BenchmarkCase)
    if not cases:
        parser.error("The case dataset must not be empty")
    asyncio.run(
        run_experiment(
            manifest,
            cases,
            args.output_dir,
            fixture_responses=args.fixture_responses,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())