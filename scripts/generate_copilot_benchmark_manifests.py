"""Generate comparable Copilot Studio manifests for all repository patterns."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.benchmarking.fingerprinting import fingerprint_files, fingerprint_json
from src.benchmarking.models import ExperimentManifest

PATTERNS = {
    "A": "copilot_studio_native_search",
    "A2": "copilot_studio_foundry_iq",
    "B": "copilot_studio_foundry_agent",
    "C": "copilot_studio_lookup_action",
    "Hosted": "copilot_studio_hosted_agent",
}


def _git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def generate(
    *,
    pattern: str,
    agent_name: str,
    agent_source: Path,
    dataset: Path,
    output_dir: Path,
    corpus_fingerprint: str,
    index_fingerprint: str,
    repetitions: int,
    model_deployment: str,
) -> None:
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    dataset_fingerprint = fingerprint_json(cases)
    agent_fingerprint = fingerprint_files(agent_source)
    git_commit = _git_value("rev-parse", "HEAD")
    dirty_worktree = bool(_git_value("status", "--porcelain"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)

    retrieval_mode = PATTERNS[pattern]
    agent_slug = re.sub(r"[^a-z0-9]+", "-", agent_name.lower()).strip("-")
    manifest = ExperimentManifest(
        experiment_id=f"copilot-{agent_slug}-{pattern.lower()}-{timestamp}",
        git_commit=git_commit,
        dirty_worktree=dirty_worktree,
        dataset_name=dataset.stem,
        dataset_version=dataset_fingerprint,
        corpus_fingerprint=corpus_fingerprint,
        index_fingerprint=index_fingerprint,
        pattern=pattern,  # type: ignore[arg-type]
        retrieval_mode=retrieval_mode,
        invocation_path=f"copilot_studio_direct_line:{agent_name}",
        output_mode="answer_with_citations",
        model_deployment=model_deployment,
        configuration_version=agent_fingerprint,
        knowledge_source_settings={"copilot_studio_agent": agent_name},
        warmup_count=1,
        measured_repetitions=repetitions,
        concurrency=1,
        timeout_seconds=60,
    )
    path = output_dir / f"copilot-{agent_slug}.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", choices=PATTERNS, required=True)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--agent-source", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--corpus-fingerprint", required=True)
    parser.add_argument("--index-fingerprint", required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model-deployment", required=True)
    args = parser.parse_args()
    generate(
        pattern=args.pattern,
        agent_name=args.agent_name,
        agent_source=args.agent_source,
        dataset=args.dataset,
        output_dir=args.output_dir,
        corpus_fingerprint=args.corpus_fingerprint,
        index_fingerprint=args.index_fingerprint,
        repetitions=args.repetitions,
        model_deployment=args.model_deployment,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())