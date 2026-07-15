"""Unit tests for the deterministic evaluation graders (P1.5)."""

from __future__ import annotations

from pathlib import Path

from src.evaluation.graders import (
    grade_case,
    is_refusal,
    policy_number_cited,
    summarize,
    title_mentioned,
)
from src.evaluation.run_eval import evaluate, load_dataset

_DATASET = Path(__file__).resolve().parents[1] / "eval" / "datasets" / "hr_qa_testset.csv"


def test_is_refusal_detects_standard_message():
    assert is_refusal(
        "I could not find this information in the HR policy documents. "
        "Please contact your HR representative for assistance."
    )
    assert not is_refusal("Per Policy 51350, full-time employees accrue PTO.")


def test_policy_number_cited_whole_token_only():
    assert policy_number_cited("See Policy 51350 - PTO.", [], "51350")
    # 5135 must not match inside 51350
    assert not policy_number_cited("See Policy 51350 - PTO.", [], "5135")


def test_policy_number_cited_in_citations():
    citations = [{"policy_number": "52005", "title": "Uniform Dress Code"}]
    assert policy_number_cited("The dress code is defined here.", citations, "52005")


def test_title_mentioned_threshold():
    assert title_mentioned("This is about Short-Term Disability benefits.", [], "Short-Term Disability")
    assert not title_mentioned("This is about parking.", [], "Short-Term Disability")


def test_grade_case_positive():
    result = {
        "answer": "Per Policy 51350 - Types of Leave: Paid Time Off (PTO), you accrue PTO.",
        "citations": [{"policy_number": "51350"}],
    }
    expected = {
        "test_case": "pto-accrual",
        "expected_policy_number": "51350",
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
        "expected_policy_number": "51350",
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
            {"answer": "Policy 51350 covers PTO.", "citations": [{"n": "51350"}]},
            {"test_case": "a", "expected_policy_number": "51350", "expected_policy_title": "PTO"},
        ),
        grade_case(
            {"answer": "no idea", "citations": []},
            {"test_case": "b", "expected_policy_number": "52005", "expected_policy_title": "Dress Code"},
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
