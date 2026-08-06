"""Deterministic quality metrics over normalized benchmark results."""

from __future__ import annotations

from enum import StrEnum

from src.benchmarking.models import CaseResult
from src.evaluation.graders import grade_case


class EvaluationCategory(StrEnum):
    EXACT_LOOKUP = "exact_lookup"
    DIRECT_FACT = "direct_fact"
    DISAMBIGUATION = "disambiguation"
    DOCUMENT_LOCATION = "document_location"
    MULTI_POLICY_SYNTHESIS = "multi_policy_synthesis"
    ADVERSARIAL_OUT_OF_DOMAIN = "adversarial_out_of_domain"
    PARAPHRASE_SYNONYM = "paraphrase_synonym"
    PERMISSION_SECURITY = "permission_security"


def retrieval_metrics(
    returned_source_ids: list[str], expected_source_ids: list[str]
) -> dict[str, float]:
    """Compute hit/recall/precision at k and reciprocal rank."""
    expected = set(expected_source_ids)
    if not expected:
        return {}
    metrics: dict[str, float] = {}
    for k in (1, 3, 5):
        returned = returned_source_ids[:k]
        hits = len(expected.intersection(returned))
        metrics[f"hit_at_{k}"] = float(hits > 0)
        metrics[f"recall_at_{k}"] = hits / len(expected)
        metrics[f"precision_at_{k}"] = hits / len(returned) if returned else 0.0
    first_rank = next(
        (rank for rank, source_id in enumerate(returned_source_ids, 1) if source_id in expected),
        None,
    )
    metrics["mrr"] = 1.0 / first_rank if first_rank else 0.0
    return metrics


def apply_deterministic_evaluation(
    result: CaseResult,
    *,
    answer: str,
    expected_policy_number: str,
    expected_policy_title: str,
) -> CaseResult:
    """Join target-repo citation/refusal graders into normalized local metrics."""
    citations = [
        {"policy_number": reference.policy_number, "title": reference.title}
        for reference in result.references
    ]
    grade = grade_case(
        {"answer": answer, "citations": citations},
        {
            "test_case": result.case_id,
            "expected_policy_number": expected_policy_number,
            "expected_policy_title": expected_policy_title,
        },
    )
    return result.model_copy(
        update={
            "local_metrics": {
                **result.local_metrics,
                **{name: value for name, value in grade.metrics.items()},
                "deterministic_pass": grade.passed,
            }
        }
    )