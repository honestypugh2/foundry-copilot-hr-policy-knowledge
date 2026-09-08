"""Log the jailbreak / secret-disclosure cases to the Foundry project.

Runs the deployed Foundry agent (or precomputed answers) on the ``security``
cases and uploads a ``SecurityRefusalEvaluator`` result through
``azure-ai-evaluation`` so the checks appear in the Foundry portal Evaluations
alongside the benchmark's authoritative deterministic gate.

Examples::

    # Live against a deployed Foundry hosted agent (Pattern B or Hosted)
    python -m scripts.evaluate_security_foundry \
      --agent-name hr-policy-agent \
      --cases experiments/datasets/copilot-hr-policy-release-v2.json \
      --evaluation-spec experiments/datasets/copilot-hr-policy-release-v2-evaluation.json \
      --evaluation-name jailbreak-hosted-release-v2 \
      --output-dir experiments/reports/<experiment-id>/security-portal

    # Reuse captured answers (jsonl of {"case_id","answer","citations"}), no live call
    python -m scripts.evaluate_security_foundry --answers captured.jsonl ...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.evaluation.security_evaluator import SecurityRefusalEvaluator


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _answers_from_agent(agent_name: str, queries: dict[str, str]) -> dict[str, dict[str, Any]]:
    from src.benchmarking.adapters.foundry_hosted import build_foundry_hosted_answer

    answer_fn = build_foundry_hosted_answer(agent_name)

    async def _run() -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for case_id, query in queries.items():
            results[case_id] = await answer_fn(query)
        return results

    return asyncio.run(_run())


def _answers_from_file(path: Path) -> dict[str, dict[str, Any]]:
    answers: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        case_id = record.get("case_id")
        if not case_id:
            continue
        answers[case_id] = {
            "answer": record.get("answer", ""),
            "citations": record.get("citations", []),
        }
    return answers


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Log jailbreak/security cases to the Foundry project")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluation-name", default="hr-policy-jailbreak-security")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--agent-name", help="Deployed Foundry agent to invoke live, e.g. hr-policy-agent")
    source.add_argument("--answers", type=Path, help="JSONL of {case_id, answer, citations} to reuse")
    parser.add_argument("--project-endpoint", help="Override AZURE_AI_PROJECT_ENDPOINT")
    args = parser.parse_args(argv)

    project_endpoint = (
        args.project_endpoint
        or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    )
    if not project_endpoint:
        parser.error("AZURE_AI_PROJECT_ENDPOINT is required to upload results to the Foundry project")

    cases = {case["case_id"]: case for case in _load_json(args.cases)}
    specs = [spec for spec in _load_json(args.evaluation_spec) if spec.get("scope") == "security"]
    if not specs:
        parser.error("The evaluation spec has no security-scope cases")

    queries = {spec["case_id"]: cases[spec["case_id"]]["query"] for spec in specs}
    answers = _answers_from_agent(args.agent_name, queries) if args.agent_name else _answers_from_file(args.answers)

    rows: list[dict[str, Any]] = []
    for spec in specs:
        case_id = spec["case_id"]
        answer = answers.get(case_id)
        if answer is None:
            parser.error(f"No answer available for security case {case_id!r}")
        rows.append(
            {
                "case_id": case_id,
                "query": queries[case_id],
                "response": answer.get("answer", ""),
                "citations": answer.get("citations", []),
                "forbidden_markers": spec.get("forbidden_markers", []),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_dir / "security-dataset.jsonl"
    dataset_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result_path = args.output_dir / "security-evaluation.json"

    from azure.ai.evaluation import evaluate

    sdk_result = evaluate(
        data=str(dataset_path),
        evaluators={"security_refusal": SecurityRefusalEvaluator()},
        evaluator_config={
            "security_refusal": {
                "column_mapping": {
                    "response": "${data.response}",
                    "forbidden_markers": "${data.forbidden_markers}",
                    "citations": "${data.citations}",
                }
            }
        },
        azure_ai_project=project_endpoint,
        evaluation_name=args.evaluation_name,
        output_path=str(result_path),
        fail_on_evaluator_errors=True,
    )

    metrics = dict(sdk_result.get("metrics", {}))
    print(f"Uploaded '{args.evaluation_name}' to the Foundry project: {project_endpoint}")
    print(f"Security metrics: {metrics}")
    studio_url = sdk_result.get("studio_url")
    if studio_url:
        print(f"Portal: {studio_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
