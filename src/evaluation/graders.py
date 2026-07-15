"""
Deterministic graders for HR policy answers (P1.5 — evaluation harness).

These graders are **pure functions** that require no Azure/LLM access, so they
run in CI and give an auditable, reproducible signal for the anti-hallucination
guarantees the agent instructions make (``tool_choice="required"`` guarantees
the tool is *called*, not that the answer is *grounded* — these graders check
the answer itself).

Metrics per test case:

- ``policy_number_cited`` — the expected policy number appears in the answer
  text or in a citation. This is the core citation-accuracy signal.
- ``title_mentioned`` — a meaningful share of the expected policy title tokens
  appear in the answer.
- ``citation_present`` — the agent returned at least one structured citation.
- ``correct_refusal`` — for out-of-scope questions (no expected policy) the
  agent produced the standard grounded-refusal message rather than answering
  from general knowledge.
- ``wrongful_refusal`` — the agent refused even though a policy was expected
  (a grounding/recall failure).

For LLM-graded groundedness/relevance, see ``run_eval.py`` (optional, uses
``azure-ai-evaluation``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# The canonical grounded-refusal phrase emitted by the agent instructions.
REFUSAL_MARKERS = (
    "could not find this information in the hr policy documents",
    "please contact your hr representative",
)

# Tokens ignored when comparing policy titles.
_TITLE_STOPWORDS = frozenset(
    {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "matters", "related"}
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_refusal(answer: str) -> bool:
    """Return True if the answer is the standard grounded-refusal message."""
    normalized = _normalize(answer)
    return any(marker in normalized for marker in REFUSAL_MARKERS)


def _citation_blob(citations: Sequence[Mapping[str, Any]] | None) -> str:
    if not citations:
        return ""
    fragments: list[str] = []
    for citation in citations:
        if isinstance(citation, Mapping):
            fragments.extend(str(v) for v in citation.values())
        else:
            fragments.append(str(citation))
    return _normalize(" ".join(fragments))


def policy_number_cited(
    answer: str,
    citations: Sequence[Mapping[str, Any]] | None,
    expected_policy_number: str,
) -> bool:
    """Check the expected policy number appears in the answer or a citation.

    Matches the number as a whole token so ``5135`` does not match ``51350``.
    """
    expected = (expected_policy_number or "").strip()
    if not expected:
        return False
    haystack = _normalize(answer) + " " + _citation_blob(citations)
    return re.search(rf"(?<!\d){re.escape(expected)}(?!\d)", haystack) is not None


def title_mentioned(
    answer: str,
    citations: Sequence[Mapping[str, Any]] | None,
    expected_policy_title: str,
    threshold: float = 0.6,
) -> bool:
    """Return True if enough significant title tokens appear in the answer.

    ``threshold`` is the fraction of non-stopword title tokens that must be
    present in the answer or citations.
    """
    tokens = [
        t
        for t in re.findall(r"[a-z0-9]+", _normalize(expected_policy_title))
        if t not in _TITLE_STOPWORDS
    ]
    if not tokens:
        return False
    haystack = _normalize(answer) + " " + _citation_blob(citations)
    hits = sum(1 for t in tokens if t in haystack)
    return (hits / len(tokens)) >= threshold


@dataclass
class GraderResult:
    """Per-test-case grading outcome."""

    test_case: str
    passed: bool
    metrics: dict[str, bool] = field(default_factory=dict)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "test_case": self.test_case,
            "passed": self.passed,
            "metrics": self.metrics,
            "notes": self.notes,
        }


def grade_case(
    result: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> GraderResult:
    """Grade a single agent answer against its expected reference.

    Args:
        result: The agent output, e.g. ``{"answer": str, "citations": [...]}``.
        expected: A test-set row with ``test_case``, ``expected_policy_number``
            and ``expected_policy_title``. An empty policy number marks an
            out-of-scope (negative) case where a refusal is the correct answer.
    """
    answer = str(result.get("answer", ""))
    citations = result.get("citations") or []

    test_case = str(expected.get("test_case", "")) or "unnamed"
    expected_number = str(expected.get("expected_policy_number", "") or "").strip()
    expected_title = str(expected.get("expected_policy_title", "") or "").strip()

    refused = is_refusal(answer)
    metrics: dict[str, bool] = {}

    if not expected_number:
        # Negative / out-of-scope case: the correct behaviour is a refusal.
        metrics["correct_refusal"] = refused
        passed = refused
        notes = "" if refused else "Expected a grounded refusal but the agent answered."
        return GraderResult(test_case, passed, metrics, notes)

    number_ok = policy_number_cited(answer, citations, expected_number)
    title_ok = title_mentioned(answer, citations, expected_title)
    citation_ok = len(citations) > 0
    wrongful_refusal = refused

    metrics.update(
        {
            "policy_number_cited": number_ok,
            "title_mentioned": title_ok,
            "citation_present": citation_ok,
            "wrongful_refusal": wrongful_refusal,
        }
    )

    # A case passes when the expected policy number is cited and the agent did
    # not wrongly refuse. Title/citation presence are quality signals.
    passed = number_ok and not wrongful_refusal
    notes = ""
    if wrongful_refusal:
        notes = "Agent refused despite an expected policy match (recall failure)."
    elif not number_ok:
        notes = f"Expected policy number {expected_number} not cited."

    return GraderResult(test_case, passed, metrics, notes)


def summarize(results: Sequence[GraderResult]) -> dict[str, Any]:
    """Aggregate grader results into pass-rate and per-metric statistics."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    metric_totals: dict[str, int] = {}
    metric_hits: dict[str, int] = {}
    for r in results:
        for name, value in r.metrics.items():
            metric_totals[name] = metric_totals.get(name, 0) + 1
            metric_hits[name] = metric_hits.get(name, 0) + (1 if value else 0)

    metric_rates = {
        name: round(metric_hits[name] / metric_totals[name], 3)
        for name in metric_totals
    }

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "metric_rates": metric_rates,
        "failures": [r.test_case for r in results if not r.passed],
    }
