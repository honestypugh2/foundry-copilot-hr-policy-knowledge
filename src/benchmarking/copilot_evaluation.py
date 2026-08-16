"""Normalize native Copilot Studio Evaluation evidence for benchmark reports."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.benchmarking.aggregation import wilson_score_interval
from src.benchmarking.evaluation_attachment import (
    deterministic_grade,
    summarize_deterministic_categories,
)
from src.benchmarking.models import BenchmarkCase

EXPORT_COLUMNS = {
    "Question",
    "Expected response",
    "Test method",
    "Passing score",
    "Agent response",
    "Test result",
    "Analysis",
}
WIDE_EXPORT_COLUMNS = {
    "conversationId",
    "question",
    "expectedResponse",
    "actualResponse",
    "testMethodType_1",
    "result_1",
    "passingScore_1",
    "explanation_1",
    "testMethodType_2",
    "result_2",
    "passingScore_2",
    "explanation_2",
}
DEFAULT_REQUIRED_METHODS = ("General quality", "Compare meaning")
NATIVE_STATUSES = {"Pass", "Fail", "Error", "Invalid"}
POLICY_REFERENCE = re.compile(r"\bPolicy\s+(?P<number>\d{5})\b", re.IGNORECASE)

# GitHub Copilot Harness "Conversation" export: one turn per column, single
# GeneralQuality method, no API run artifact to cross-check.
CONVERSATION_EXPORT_COLUMNS = {
    "conversation",
    "expectedResponse",
    "actualResponse",
    "testMethodType_1",
    "result_1",
    "passingScore_1",
    "explanation_1",
}
_CONVERSATION_SPLIT = re.compile(r"\bAgent response:\s*", re.IGNORECASE)
_CONVERSATION_QUESTION = re.compile(r"^\s*Question:\s*", re.IGNORECASE)


def _parse_conversation_cell(cell: str) -> tuple[str, str]:
    """Split a GitHub Copilot Harness conversation cell into question and answer."""
    parts = _CONVERSATION_SPLIT.split(cell, maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Conversation cell missing an 'Agent response:' delimiter")
    question = _CONVERSATION_QUESTION.sub("", parts[0]).strip()
    answer = parts[1].strip()
    if not question or not answer:
        raise ValueError("Conversation cell has an empty question or answer")
    return question, answer


def sanitize_native_run(run: dict[str, Any]) -> dict[str, Any]:
    """Keep correlation/status evidence without grader explanations or payload text."""
    fields = (
        "id",
        "environmentId",
        "cdsBotId",
        "ownerId",
        "testSetId",
        "state",
        "startTime",
        "endTime",
        "name",
        "totalTestCases",
        "mcsConnectionId",
    )
    sanitized = {field: run.get(field) for field in fields}
    sanitized["testCasesResults"] = [
        {
            "testCaseId": case.get("testCaseId"),
            "state": case.get("state"),
            "metricsResults": [
                {
                    "type": metric.get("type"),
                    "result": {
                        "status": (
                            metric.get("result", {}).get("status")
                            if isinstance(metric.get("result"), dict)
                            else None
                        )
                    },
                }
                for metric in case.get("metricsResults", [])
                if isinstance(metric, dict)
            ],
        }
        for case in run.get("testCasesResults", [])
        if isinstance(case, dict)
    ]
    return sanitized


def _load_array(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return payload


def _method_key(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _passing_score(value: str) -> float:
    normalized = value.strip().removesuffix("%").strip()
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid Compare meaning passing score: {value!r}") from exc


def _summary(passes: list[bool]) -> dict[str, Any]:
    if not passes:
        raise ValueError("Cannot summarize an empty evaluation scope")
    passed = sum(passes)
    count = len(passes)
    return {
        "passed": passed,
        "count": count,
        "pass_rate": passed / count,
        "confidence_interval": wilson_score_interval(passed, count).model_dump(
            mode="json"
        ),
    }


def _native_summary(statuses: list[str]) -> dict[str, Any]:
    if not statuses:
        raise ValueError("Cannot summarize an empty native evaluation method")
    counts = Counter(statuses)
    return {
        "passed": counts["Pass"],
        "failed": counts["Fail"],
        "errors": counts["Error"],
        "invalid": counts["Invalid"],
        "count": len(statuses),
        "pass_rate": counts["Pass"] / len(statuses),
    }


def _canonical_export_rows(
    reader: csv.DictReader[str],
) -> list[dict[str, str]]:
    columns = set(reader.fieldnames or [])
    source_rows = list(reader)
    if columns == EXPORT_COLUMNS:
        return source_rows
    if columns != WIDE_EXPORT_COLUMNS:
        raise ValueError(
            "Copilot Studio export columns do not match a supported portal schema"
        )
    rows: list[dict[str, str]] = []
    for source in source_rows:
        for index in (1, 2):
            rows.append(
                {
                    "Question": source["question"],
                    "Expected response": source["expectedResponse"],
                    "Test method": source[f"testMethodType_{index}"],
                    "Passing score": source[f"passingScore_{index}"],
                    "Agent response": source["actualResponse"],
                    "Test result": source[f"result_{index}"],
                    "Analysis": source[f"explanation_{index}"],
                }
            )
    return rows


def _validate_native_run(
    run: dict[str, Any],
    *,
    expected_case_count: int,
    expected_environment_id: str | None,
    expected_bot_id: str | None,
    expected_test_set_id: str | None,
    required_methods: tuple[str, ...],
    allow_nondecisive: bool,
) -> dict[str, Any]:
    if run.get("state") != "Completed":
        raise ValueError(f"Native evaluation run state is {run.get('state')!r}")
    expected_values = {
        "environmentId": expected_environment_id,
        "cdsBotId": expected_bot_id,
        "testSetId": expected_test_set_id,
    }
    for field, expected in expected_values.items():
        if expected and str(run.get(field, "")).lower() != expected.lower():
            raise ValueError(f"Native evaluation run has unexpected {field}")
    if run.get("totalTestCases") != expected_case_count:
        raise ValueError(
            "Native evaluation run case count does not match the benchmark dataset"
        )
    results = run.get("testCasesResults")
    if not isinstance(results, list) or len(results) != expected_case_count:
        raise ValueError("Native evaluation run has incomplete test-case results")
    required_keys = {_method_key(method) for method in required_methods}
    status_counts: dict[str, Counter[str]] = {
        method: Counter() for method in required_methods
    }
    display_by_key = {_method_key(method): method for method in required_methods}
    for case in results:
        allowed_case_states = {"Completed", "Error"} if allow_nondecisive else {"Completed"}
        if not isinstance(case, dict) or case.get("state") not in allowed_case_states:
            raise ValueError("Native evaluation contains a noncompleted test case")
        metrics = case.get("metricsResults")
        if not isinstance(metrics, list):
            raise ValueError("Native evaluation test case has no metric results")
        seen: set[str] = set()
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            key = _method_key(str(metric.get("type") or ""))
            if key not in required_keys:
                continue
            if key in seen:
                raise ValueError("Native evaluation contains a duplicate metric")
            seen.add(key)
            result = metric.get("result")
            status = str(result.get("status") if isinstance(result, dict) else "")
            if status not in NATIVE_STATUSES:
                raise ValueError(f"Native evaluation metric has unknown status {status!r}")
            if status not in {"Pass", "Fail"} and not allow_nondecisive:
                raise ValueError(
                    f"Native evaluation metric has nondecisive status {status!r}"
                )
            status_counts[display_by_key[key]][status] += 1
        if seen != required_keys:
            raise ValueError("Native evaluation test case is missing a required method")
    return {
        method: _native_summary(list(counts.elements()))
        for method, counts in status_counts.items()
    }


def import_copilot_evaluation(
    *,
    export_csv_path: Path,
    cases_path: Path,
    specifications_path: Path,
    native_run_path: Path,
    experiment_id: str,
    dataset_version: str,
    expected_environment_id: str | None = None,
    expected_bot_id: str | None = None,
    expected_test_set_id: str | None = None,
    required_methods: tuple[str, ...] = DEFAULT_REQUIRED_METHODS,
    expected_compare_meaning_score: float = 70,
    allow_nondecisive: bool = False,
) -> dict[str, Any]:
    cases = {
        case.case_id: case
        for case in (
            BenchmarkCase.model_validate(item) for item in _load_array(cases_path)
        )
    }
    specifications = _load_array(specifications_path)
    expected_by_question: dict[str, tuple[BenchmarkCase | None, dict[str, Any]]] = {}
    for specification in specifications:
        case = cases.get(str(specification["case_id"]))
        query = str(specification.get("query") or (case.query if case else "")).strip()
        if not query:
            raise ValueError(f"No query configured for {specification['case_id']}")
        if query in expected_by_question:
            raise ValueError(f"Duplicate benchmark question: {query!r}")
        expected_by_question[query] = (case, specification)

    with export_csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = _canonical_export_rows(reader)

    required_keys = {_method_key(method) for method in required_methods}
    display_by_key = {_method_key(method): method for method in required_methods}
    rows_by_question: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        question = str(row.get("Question") or "").strip()
        if question not in expected_by_question:
            raise ValueError(f"Unknown Copilot Studio evaluation question: {question!r}")
        method_key = _method_key(str(row.get("Test method") or ""))
        if method_key not in required_keys:
            continue
        question_rows = rows_by_question.setdefault(question, {})
        if method_key in question_rows:
            raise ValueError(
                f"Duplicate {display_by_key[method_key]} row for {question!r}"
            )
        status = str(row.get("Test result") or "").strip()
        if status not in NATIVE_STATUSES:
            raise ValueError(
                f"Evaluation result for {question!r} is unknown: {status!r}"
            )
        if status not in {"Pass", "Fail"} and not allow_nondecisive:
            raise ValueError(
                f"Evaluation result for {question!r} is nondecisive: {status!r}"
            )
        if method_key == _method_key("Compare meaning") and _passing_score(
            str(row.get("Passing score") or "")
        ) != expected_compare_meaning_score:
            raise ValueError(
                f"Compare meaning passing score must be {expected_compare_meaning_score:g}"
            )
        question_rows[method_key] = row

    if set(rows_by_question) != set(expected_by_question):
        missing = sorted(set(expected_by_question) - set(rows_by_question))
        raise ValueError(f"Copilot Studio export is missing questions: {missing}")

    records: list[dict[str, Any]] = []
    method_statuses: dict[str, list[str]] = {
        method: [] for method in required_methods
    }
    for question, (case, specification) in expected_by_question.items():
        question_rows = rows_by_question[question]
        if set(question_rows) != required_keys:
            raise ValueError(f"Evaluation methods are incomplete for {question!r}")
        answers = {
            str(row.get("Agent response") or "").strip()
            for row in question_rows.values()
        }
        if len(answers) != 1:
            raise ValueError(
                f"Evaluation methods contain inconsistent responses for {question!r}"
            )
        expected_responses = {
            str(row.get("Expected response") or "").strip()
            for row in question_rows.values()
        }
        if len(expected_responses) != 1 or not next(iter(expected_responses), ""):
            raise ValueError(
                f"Evaluation methods contain a missing or inconsistent expected response for {question!r}"
            )
        answer = answers.pop()
        citations = [
            {"policy_number": match.group("number")}
            for match in POLICY_REFERENCE.finditer(answer)
        ]
        deterministic_pass, metrics = deterministic_grade(
            answer=answer,
            citations=citations,
            specification=specification,
        )
        native_results = {
            display_by_key[key]: row["Test result"]
            for key, row in question_rows.items()
        }
        for method, status in native_results.items():
            method_statuses[method].append(status)
        records.append(
            {
                "case_id": specification["case_id"],
                "category": case.category if case else "security",
                "scope": specification["scope"],
                "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
                "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                "native_results": native_results,
                "deterministic_pass": deterministic_pass,
                "deterministic_metrics": metrics,
            }
        )

    native_run = json.loads(native_run_path.read_text(encoding="utf-8"))
    if not isinstance(native_run, dict):
        raise ValueError("Native evaluation run artifact must be a JSON object")
    api_method_summaries = _validate_native_run(
        native_run,
        expected_case_count=len(expected_by_question),
        expected_environment_id=expected_environment_id,
        expected_bot_id=expected_bot_id,
        expected_test_set_id=expected_test_set_id,
        required_methods=required_methods,
        allow_nondecisive=allow_nondecisive,
    )
    csv_method_summaries = {
        method: _native_summary(statuses)
        for method, statuses in method_statuses.items()
    }
    for method in required_methods:
        for field in ("passed", "failed", "errors", "invalid", "count"):
            if (
                api_method_summaries[method][field]
                != csv_method_summaries[method][field]
            ):
                raise ValueError(f"API and CSV {field} counts disagree for {method}")

    quality_records = [record for record in records if record["scope"] == "quality"]
    security_records = [record for record in records if record["scope"] == "security"]
    if not quality_records or not security_records:
        raise ValueError("Evaluation requires both quality and security cases")
    dataset_fingerprint = hashlib.sha256(
        json.dumps(
            [
                {
                    "question": question,
                    "specification": expected_by_question[question][1],
                }
                for question in sorted(expected_by_question)
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    release_blockers = [
        f"{method}: {summary['errors']} Error and {summary['invalid']} Invalid results"
        for method, summary in csv_method_summaries.items()
        if summary["errors"] or summary["invalid"]
    ]
    return {
        "schema_version": "1.0",
        "artifact_type": "copilot_studio_native_evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "dataset_version": dataset_version,
        "dataset_fingerprint": dataset_fingerprint,
        "evaluation_run_id": native_run.get("id"),
        "test_set_id": native_run.get("testSetId"),
        "environment_id": native_run.get("environmentId"),
        "bot_id": native_run.get("cdsBotId"),
        "run_name": native_run.get("name"),
        "run_started_at": native_run.get("startTime"),
        "run_ended_at": native_run.get("endTime"),
        "user_profile_connection_id": native_run.get("mcsConnectionId"),
        "quality_measurement": "copilot_studio_native_evaluation_export",
        "measurement_relationship": (
            "separate_same_published_agent_testset_replay"
        ),
        "native_release_ready": not release_blockers,
        "native_release_blockers": release_blockers,
        "native_methods": csv_method_summaries,
        "deterministic_quality": _summary(
            [record["deterministic_pass"] for record in quality_records]
        ),
        "deterministic_security": _summary(
            [record["deterministic_pass"] for record in security_records]
        ),
        "quality_by_category": summarize_deterministic_categories(quality_records),
        "security_by_category": summarize_deterministic_categories(security_records),
        "cases": records,
    }


def import_github_copilot_conversation_evaluation(
    *,
    export_csv_path: Path,
    cases_path: Path,
    specifications_path: Path,
    experiment_id: str,
    dataset_version: str,
    quality_method: str = "General quality",
    run_name: str | None = None,
) -> dict[str, Any]:
    """Normalize a GitHub Copilot Harness 'Conversation' evaluation export.

    This harness embeds each turn in one column, carries a single GeneralQuality
    method, and emits no API run artifact to cross-check. Deterministic gates
    re-grade the agent responses; the native GeneralQuality status is recorded
    for provenance only (it penalizes correct refusals, so it is not trusted).
    """
    cases = {
        case.case_id: case
        for case in (
            BenchmarkCase.model_validate(item) for item in _load_array(cases_path)
        )
    }
    specifications = _load_array(specifications_path)
    expected_by_question: dict[str, tuple[BenchmarkCase | None, dict[str, Any]]] = {}
    for specification in specifications:
        case = cases.get(str(specification["case_id"]))
        query = str(specification.get("query") or (case.query if case else "")).strip()
        if not query:
            raise ValueError(f"No query configured for {specification['case_id']}")
        if query in expected_by_question:
            raise ValueError(f"Duplicate benchmark question: {query!r}")
        expected_by_question[query] = (case, specification)

    with export_csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != CONVERSATION_EXPORT_COLUMNS:
            raise ValueError(
                "Export columns do not match the GitHub Copilot Harness "
                "conversation schema"
            )
        source_rows = list(reader)

    records: list[dict[str, Any]] = []
    native_statuses: list[str] = []
    seen_questions: set[str] = set()
    for source in source_rows:
        question, answer = _parse_conversation_cell(
            str(source.get("conversation") or "")
        )
        if question not in expected_by_question:
            raise ValueError(f"Unknown evaluation question: {question!r}")
        if question in seen_questions:
            raise ValueError(f"Duplicate conversation row for {question!r}")
        seen_questions.add(question)
        case, specification = expected_by_question[question]
        native_statuses.append(str(source.get("result_1") or "").strip())
        citations = [
            {"policy_number": match.group("number")}
            for match in POLICY_REFERENCE.finditer(answer)
        ]
        deterministic_pass, metrics = deterministic_grade(
            answer=answer,
            citations=citations,
            specification=specification,
        )
        records.append(
            {
                "case_id": specification["case_id"],
                "category": case.category if case else "security",
                "scope": specification["scope"],
                "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
                "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                "native_general_quality": native_statuses[-1],
                "deterministic_pass": deterministic_pass,
                "deterministic_metrics": metrics,
            }
        )

    if seen_questions != set(expected_by_question):
        missing = sorted(set(expected_by_question) - seen_questions)
        raise ValueError(f"Conversation export is missing questions: {missing}")

    quality_records = [record for record in records if record["scope"] == "quality"]
    security_records = [record for record in records if record["scope"] == "security"]
    if not quality_records or not security_records:
        raise ValueError("Evaluation requires both quality and security cases")

    native_counts = Counter(native_statuses)
    # Statuses outside Pass/Fail (e.g. GitHub Copilot Harness "MakerError") are
    # nondecisive and recorded as release-blocking evidence.
    error_count = sum(
        count
        for status, count in native_counts.items()
        if status not in {"Pass", "Fail"}
    )
    native_summary = {
        quality_method: {
            "passed": native_counts["Pass"],
            "failed": native_counts["Fail"],
            "errors": error_count,
            "invalid": native_counts["Invalid"],
            "count": len(native_statuses),
            "pass_rate": native_counts["Pass"] / len(native_statuses),
        }
    }
    release_blockers = (
        [f"{quality_method}: {error_count} nondecisive native results"]
        if error_count
        else []
    )
    dataset_fingerprint = hashlib.sha256(
        json.dumps(
            [
                {
                    "question": question,
                    "specification": expected_by_question[question][1],
                }
                for question in sorted(expected_by_question)
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "artifact_type": "copilot_studio_native_evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "dataset_version": dataset_version,
        "dataset_fingerprint": dataset_fingerprint,
        "run_name": run_name,
        "evaluation_harness": "github_copilot_conversation",
        "quality_measurement": "copilot_studio_native_evaluation_export",
        "measurement_relationship": "separate_same_published_agent_testset_replay",
        "native_release_ready": not release_blockers,
        "native_release_blockers": release_blockers,
        "native_methods": native_summary,
        "deterministic_quality": _summary(
            [record["deterministic_pass"] for record in quality_records]
        ),
        "deterministic_security": _summary(
            [record["deterministic_pass"] for record in security_records]
        ),
        "quality_by_category": summarize_deterministic_categories(quality_records),
        "security_by_category": summarize_deterministic_categories(security_records),
        "cases": records,
    }


def attach_copilot_evaluation(report_path: Path, evaluation_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    manifest = report.get("manifest", {})
    if manifest.get("experiment_id") != evaluation.get("experiment_id"):
        raise ValueError("Evaluation experiment ID does not match the report")
    if manifest.get("dataset_version") != evaluation.get("dataset_version"):
        raise ValueError("Evaluation dataset version does not match the report")
    provenance = report["aggregate"]["provenance"]
    if provenance.get("measurement_boundary") != "copilot_studio_direct_line":
        raise ValueError(
            "Native Copilot Studio evaluation can only attach to a Direct Line report"
        )
    provenance.update(
        {
            "quality": evaluation["deterministic_quality"]["pass_rate"],
            "quality_measurement": evaluation["quality_measurement"],
            "security_pass_rate": evaluation["deterministic_security"]["pass_rate"],
            "security_measurement": "deterministic_native_response_export",
            "measurement_relationship": evaluation["measurement_relationship"],
            "evaluation_run_id": evaluation.get("evaluation_run_id"),
            "evaluation_test_set_id": evaluation.get("test_set_id"),
            "evaluation_dataset_fingerprint": evaluation["dataset_fingerprint"],
            "evaluation_native_methods": evaluation["native_methods"],
            "evaluation_release_ready": evaluation["native_release_ready"],
            "evaluation_release_blockers": evaluation["native_release_blockers"],
            "evaluation_artifact": evaluation_path.name,
        }
    )
    report["aggregate"]["quality_by_category"] = evaluation["quality_by_category"]
    report["aggregate"]["security_by_category"] = evaluation[
        "security_by_category"
    ]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path = report_path.with_suffix(".md")
    if markdown_path.exists():
        marker = "\n## Copilot Studio native Evaluation\n"
        original = markdown_path.read_text(encoding="utf-8").split(marker, 1)[0]
        methods = "\n".join(
            f"| {name} | {summary['passed']}/{summary['count']} "
            f"({summary['pass_rate']:.1%}) |"
            for name, summary in evaluation["native_methods"].items()
        )
        release_ready = "Yes" if evaluation["native_release_ready"] else "No"
        release_blockers = "; ".join(evaluation["native_release_blockers"]) or "None"
        markdown_path.write_text(
            original
            + marker
            + "\nThis is a separate replay through the same published agent and "
            + "test set; it did not grade the timed Direct Line responses.\n\n"
            + "| Signal | Result |\n"
            + "| --- | ---: |\n"
            + methods
            + "\n"
            + f"| Deterministic quality | {evaluation['deterministic_quality']['passed']}/"
            + f"{evaluation['deterministic_quality']['count']} "
            + f"({evaluation['deterministic_quality']['pass_rate']:.1%}) |\n"
            + f"| Deterministic security | {evaluation['deterministic_security']['passed']}/"
            + f"{evaluation['deterministic_security']['count']} "
            + f"({evaluation['deterministic_security']['pass_rate']:.1%}) |\n"
            + f"| Native release ready | {release_ready} |\n"
            + f"| Native release blockers | {release_blockers} |\n"
            + f"| Evaluation run ID | `{evaluation.get('evaluation_run_id') or '—'}` |\n"
            + f"| Test set ID | `{evaluation.get('test_set_id') or '—'}` |\n",
            encoding="utf-8",
        )
