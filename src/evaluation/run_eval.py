"""
HR policy agent evaluation runner (P1.5).

Loads the shared test set, obtains an answer for each question, applies the
deterministic graders in :mod:`src.evaluation.graders`, and (optionally) the
LLM-graded evaluators from ``azure-ai-evaluation``. Emits a summary and a JSON
report.

Answer sources (pick one):

* ``--live`` — run each question through the live agent
  (:class:`~src.agents.orchestrator.HRPolicyWorkflowOrchestrator`). Requires
  Azure configuration.
* ``--answers FILE.jsonl`` — grade precomputed answers offline. Each line is
  ``{"test_case": "...", "answer": "...", "citations": [...]}``. This path
  needs no Azure access and is what CI uses.

Examples::

    # Offline grading of captured answers (CI-friendly)
    python -m src.evaluation.run_eval --answers runs/answers.jsonl

    # Live end-to-end evaluation against the deployed agent
    python -m src.evaluation.run_eval --live --out runs/report.json

    # Add LLM-graded groundedness/relevance (needs the 'eval' extra + Azure OpenAI)
    uv sync --extra eval
    python -m src.evaluation.run_eval --live --llm-graders

The same CSV (``eval/datasets/hr_qa_testset.csv``) can be imported into Copilot
Studio agent evaluations: map ``question`` -> Question and ``reference_answer``
-> Expected response.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from src.evaluation.graders import GraderResult, grade_case, summarize

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATASET = _REPO_ROOT / "eval" / "datasets" / "hr_qa_testset.csv"


def load_dataset(path: Path) -> list[dict[str, str]]:
    """Load the CSV test set into a list of row dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_answers(path: Path) -> dict[str, dict[str, Any]]:
    """Load precomputed answers (JSONL) keyed by ``test_case``."""
    answers: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            answers[str(record["test_case"])] = record
    return answers


async def _answer_live(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Run every question through the live orchestrator."""
    from src.agents.orchestrator import HRPolicyWorkflowOrchestrator

    orchestrator = HRPolicyWorkflowOrchestrator(use_azure=True)
    await orchestrator.initialize()

    results: dict[str, dict[str, Any]] = {}
    try:
        for row in rows:
            test_case = row["test_case"]
            logger.info("Answering %s: %s", test_case, row["question"])
            result = await orchestrator.answer_question_async(row["question"])
            results[test_case] = result
    finally:
        close = getattr(orchestrator, "close", None)
        if close is not None:
            await close()
    return results


def write_llm_evaluation_dataset(
    rows: list[dict[str, str]],
    answers: dict[str, dict[str, Any]],

    output_path: Path,
) -> int:
    """Write the sanitized JSONL accepted by Azure AI Evaluation."""
    exported = []
    for row in rows:
        result = answers.get(row["test_case"])
        if result is None:
            continue
        exported.append(
            {
                "test_case": row["test_case"],
                "query": row["question"],
                "response": str(result.get("answer", "")),
                "context": str(result.get("context") or ""),
                "ground_truth": row.get("reference_answer", ""),
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(item, ensure_ascii=True) + "\n" for item in exported),
        encoding="utf-8",
    )
    return len(exported)


def _apply_llm_graders(
    rows: list[dict[str, str]],
    answers: dict[str, dict[str, Any]],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Score groundedness/relevance through one unified SDK evaluation.

    The deterministic graders remain authoritative for CI and access-control
    assertions. This optional result is supplemental and may incur model cost.
    """
    try:
        from azure.ai.evaluation import (  # type: ignore[import-not-found]
            AzureOpenAIModelConfiguration,
            GroundednessEvaluator,
            RelevanceEvaluator,
            evaluate as evaluate_with_sdk,
        )
    except ImportError:
        logger.warning(
            "azure-ai-evaluation not installed; skipping LLM graders. "
            "Install with: uv sync --extra eval"
        )
        return {}

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    if not endpoint or not deployment:
        logger.warning(
            "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME are required; "
            "skipping LLM graders."
        )
        return {}
    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
    )
    if os.getenv("AZURE_OPENAI_API_KEY"):
        model_config["api_key"] = os.environ["AZURE_OPENAI_API_KEY"]

    credential = None
    if "api_key" not in model_config:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
    evaluators = {
        "groundedness": GroundednessEvaluator(model_config, credential=credential),
        "relevance": RelevanceEvaluator(model_config, credential=credential),
    }
    evaluator_config = {
        "groundedness": {
            "column_mapping": {
                "query": "${data.query}",
                "response": "${data.response}",
                "context": "${data.context}",
            }
        },
        "relevance": {
            "column_mapping": {
                "query": "${data.query}",
                "response": "${data.response}",
            }
        },
    }
    if output_path is not None:
        dataset_path = output_path.with_suffix(".input.jsonl")
        result_path = output_path
        write_llm_evaluation_dataset(rows, answers, dataset_path)
        sdk_result = evaluate_with_sdk(
            data=dataset_path,
            evaluators=evaluators,
            evaluator_config=evaluator_config,
            evaluation_name="hr-policy-benchmark",
            output_path=result_path,
            fail_on_evaluator_errors=False,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="hr-policy-eval-") as temp_dir:
            dataset_path = Path(temp_dir) / "input.jsonl"
            result_path = Path(temp_dir) / "results.json"
            write_llm_evaluation_dataset(rows, answers, dataset_path)
            sdk_result = evaluate_with_sdk(
                data=dataset_path,
                evaluators=evaluators,
                evaluator_config=evaluator_config,
                evaluation_name="hr-policy-benchmark",
                output_path=result_path,
                fail_on_evaluator_errors=False,
            )
    return {
        "metrics": dict(sdk_result.get("metrics", {})),
        "rows": list(sdk_result.get("rows", [])),
        "studio_url": sdk_result.get("studio_url"),
    }


def evaluate(
    rows: list[dict[str, str]],
    answers: dict[str, dict[str, Any]],
) -> list[GraderResult]:
    """Grade each test-set row against its answer."""
    results: list[GraderResult] = []
    for row in rows:
        test_case = row["test_case"]
        result = answers.get(test_case)
        if result is None:
            results.append(
                GraderResult(
                    test_case=test_case,
                    passed=False,
                    metrics={},
                    notes="No answer produced for this test case.",
                )
            )
            continue
        results.append(grade_case(result, row))
    return results


def _print_summary(summary: dict[str, Any]) -> None:
    print("\n=== HR Policy Agent Evaluation ===")
    print(f"Cases:     {summary['total']}")
    print(f"Passed:    {summary['passed']}")
    print(f"Failed:    {summary['failed']}")
    print(f"Pass rate: {summary['pass_rate'] * 100:.1f}%")
    if summary["metric_rates"]:
        print("\nMetric rates:")
        for name, rate in sorted(summary["metric_rates"].items()):
            print(f"  {name:<20} {rate * 100:5.1f}%")
    if summary["failures"]:
        print("\nFailing cases: " + ", ".join(summary["failures"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the HR policy agent.")
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument(
        "--live", action="store_true", help="Run questions through the live agent."
    )
    parser.add_argument(
        "--answers", type=Path, help="JSONL of precomputed answers to grade offline."
    )
    parser.add_argument(
        "--llm-graders",
        action="store_true",
        help="Also score groundedness/relevance via azure-ai-evaluation.",
    )
    parser.add_argument("--out", type=Path, help="Write the JSON report to this path.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    rows = load_dataset(args.dataset)

    if args.live and args.answers:
        parser.error("Choose either --live or --answers, not both.")
    if args.live:
        answers = asyncio.run(_answer_live(rows))
    elif args.answers:
        answers = load_answers(args.answers)
    else:
        parser.error("Provide --live or --answers to supply agent answers.")

    results = evaluate(rows, answers)
    summary = summarize(results)

    llm_scores: dict[str, Any] = {}
    if args.llm_graders:
        llm_output = args.out.with_suffix(".llm-evaluation.json") if args.out else None
        llm_scores = _apply_llm_graders(rows, answers, output_path=llm_output)

    _print_summary(summary)

    report = {
        "dataset": str(args.dataset),
        "summary": summary,
        "results": [r.as_dict() for r in results],
        "llm_scores": llm_scores,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written to {args.out}")

    # Non-zero exit if any case failed, so CI can gate on it.
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
