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


def _apply_llm_graders(
    rows: list[dict[str, str]],
    answers: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Optionally score groundedness/relevance with azure-ai-evaluation.

    Returns a mapping ``test_case -> {evaluator: score}``. Best-effort: if the
    package or model config is missing, returns an empty mapping.
    """
    try:
        from azure.ai.evaluation import (  # type: ignore[import-not-found]
            GroundednessEvaluator,
            RelevanceEvaluator,
        )
    except ImportError:
        logger.warning(
            "azure-ai-evaluation not installed; skipping LLM graders. "
            "Install with: uv sync --extra eval"
        )
        return {}

    model_config = {
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
    }
    if os.getenv("AZURE_OPENAI_API_KEY"):
        model_config["api_key"] = os.environ["AZURE_OPENAI_API_KEY"]

    groundedness = GroundednessEvaluator(model_config)
    relevance = RelevanceEvaluator(model_config)

    scores: dict[str, dict[str, Any]] = {}
    for row in rows:
        test_case = row["test_case"]
        result = answers.get(test_case)
        if not result:
            continue
        answer = str(result.get("answer", ""))
        context = str(result.get("context") or row.get("reference_answer", ""))
        try:
            scores[test_case] = {
                "groundedness": groundedness(
                    query=row["question"], context=context, response=answer
                ),
                "relevance": relevance(query=row["question"], response=answer),
            }
        except Exception as exc:  # pragma: no cover - depends on live service
            logger.warning("LLM grading failed for %s: %s", test_case, exc)
    return scores


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

    llm_scores: dict[str, dict[str, Any]] = {}
    if args.llm_graders:
        llm_scores = _apply_llm_graders(rows, answers)

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
