"""Unit tests for the deterministic evaluation graders (P1.5)."""

from __future__ import annotations

import json
import sys
from types import ModuleType
from pathlib import Path

from src.evaluation.graders import (
    grade_case,
    is_refusal,
    policy_number_cited,
    summarize,
    title_mentioned,
)
from src.evaluation.run_eval import (
    _apply_llm_graders,
    evaluate,
    load_dataset,
    write_llm_evaluation_dataset,
)

_DATASET = Path(__file__).resolve().parents[1] / "eval" / "datasets" / "hr_qa_testset.csv"


def test_is_refusal_detects_standard_message():
    assert is_refusal(
        "I could not find this information in the HR policy documents. "
        "Please contact your HR representative for assistance."
    )
    assert not is_refusal("Per Policy 50010, full-time employees accrue PTO.")


def test_policy_number_cited_whole_token_only():
    assert policy_number_cited("See Policy 50010 - PTO.", [], "50010")
    # 5001 must not match inside 50010
    assert not policy_number_cited("See Policy 50010 - PTO.", [], "5001")


def test_policy_number_cited_in_citations():
    citations = [{"policy_number": "60010", "title": "Uniform Dress Code"}]
    assert policy_number_cited("The dress code is defined here.", citations, "60010")


def test_title_mentioned_threshold():
    assert title_mentioned("This is about Short-Term Disability benefits.", [], "Short-Term Disability")
    assert not title_mentioned("This is about parking.", [], "Short-Term Disability")


def test_grade_case_positive():
    result = {
        "answer": "Per Policy 50010 - Types of Leave: Paid Time Off (PTO), you accrue PTO.",
        "citations": [{"policy_number": "50010"}],
    }
    expected = {
        "test_case": "pto-accrual",
        "expected_policy_number": "50010",
        "expected_policy_title": "Types of Leave: Paid Time Off (PTO)",
    }
    graded = grade_case(result, expected)
    assert graded.passed
    assert graded.metrics["policy_number_cited"]
    assert not graded.metrics["wrongful_refusal"]


def test_grade_case_wrongful_refusal_fails():
    result = {
        "answer": "I could not find this information in the HR policy documents.",
        "citations": [],
    }
    expected = {
        "test_case": "pto-accrual",
        "expected_policy_number": "50010",
        "expected_policy_title": "Paid Time Off",
    }
    graded = grade_case(result, expected)
    assert not graded.passed
    assert graded.metrics["wrongful_refusal"]


def test_grade_case_correct_refusal_for_out_of_scope():
    result = {
        "answer": "I could not find this information in the HR policy documents. "
        "Please contact your HR representative for assistance.",
        "citations": [],
    }
    expected = {
        "test_case": "out-of-scope",
        "expected_policy_number": "",
        "expected_policy_title": "",
    }
    graded = grade_case(result, expected)
    assert graded.passed
    assert graded.metrics["correct_refusal"]


def test_grade_case_hallucinated_answer_for_out_of_scope_fails():
    result = {"answer": "The weather in Seattle is sunny.", "citations": []}
    expected = {"test_case": "out-of-scope", "expected_policy_number": ""}
    graded = grade_case(result, expected)
    assert not graded.passed


def test_summarize_aggregates():
    results = [
        grade_case(
            {"answer": "Policy 50010 covers PTO.", "citations": [{"n": "50010"}]},
            {"test_case": "a", "expected_policy_number": "50010", "expected_policy_title": "PTO"},
        ),
        grade_case(
            {"answer": "no idea", "citations": []},
            {"test_case": "b", "expected_policy_number": "60010", "expected_policy_title": "Dress Code"},
        ),
    ]
    summary = summarize(results)
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["pass_rate"] == 0.5
    assert "b" in summary["failures"]


def test_dataset_loads_and_grades_perfect_reference_answers():
    """The reference answers in the test set should pass their own graders."""
    rows = load_dataset(_DATASET)
    assert rows, "test set should not be empty"
    # Build answers from the reference_answer column keyed by test_case.
    answers = {
        row["test_case"]: {"answer": row["reference_answer"], "citations": []}
        for row in rows
    }
    results = evaluate(rows, answers)
    summary = summarize(results)
    # Every reference answer is authored to cite its expected policy (or refuse).
    assert summary["pass_rate"] == 1.0, summary["failures"]


def test_llm_evaluation_export_is_jsonl_without_timestamps_or_citations(tmp_path):
    rows = load_dataset(_DATASET)[:1]
    answers = {
        rows[0]["test_case"]: {
            "answer": "Synthetic answer",
            "context": "Synthetic context",
            "citations": [{"private": "not exported"}],
        }
    }
    path = tmp_path / "evaluation.jsonl"
    assert write_llm_evaluation_dataset(rows, answers, path) == 1
    record = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert set(record) == {
        "test_case",
        "query",
        "response",
        "context",
        "ground_truth",
    }
    assert "timestamp" not in record


def test_llm_graders_use_one_unified_sdk_evaluation(monkeypatch, tmp_path):
    calls: list[dict] = []
    evaluation_module = ModuleType("azure.ai.evaluation")

    class ModelConfiguration(dict):
        def __init__(self, **kwargs):
            super().__init__(kwargs)

    class Evaluator:
        def __init__(self, model_config, credential=None):
            self.model_config = model_config
            self.credential = credential

    def fake_evaluate(**kwargs):
        calls.append(kwargs)
        records = [
            json.loads(line)
            for line in Path(kwargs["data"]).read_text(encoding="utf-8").splitlines()
        ]
        assert records[0]["query"] == "What is synthetic leave?"
        return {
            "metrics": {"groundedness": 4.0},
            "rows": [{"groundedness": 4.0}],
            "studio_url": "https://example.test/evaluation",
        }

    evaluation_module.AzureOpenAIModelConfiguration = ModelConfiguration
    evaluation_module.GroundednessEvaluator = Evaluator
    evaluation_module.RelevanceEvaluator = Evaluator
    evaluation_module.evaluate = fake_evaluate
    monkeypatch.setitem(sys.modules, "azure.ai.evaluation", evaluation_module)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.test")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "synthetic-model")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-key")

    output_path = tmp_path / "results.json"
    result = _apply_llm_graders(
        [
            {
                "test_case": "synthetic-leave",
                "question": "What is synthetic leave?",
                "reference_answer": "Synthetic reference",
            }
        ],
        {
            "synthetic-leave": {
                "answer": "Synthetic answer",
                "context": "Synthetic context",
            }
        },
        output_path=output_path,
    )

    assert len(calls) == 1
    assert set(calls[0]["evaluators"]) == {"groundedness", "relevance"}
    assert calls[0]["evaluator_config"]["groundedness"]["column_mapping"] == {
        "query": "${data.query}",
        "response": "${data.response}",
        "context": "${data.context}",
    }
    assert calls[0]["fail_on_evaluator_errors"] is False
    assert result["metrics"] == {"groundedness": 4.0}
