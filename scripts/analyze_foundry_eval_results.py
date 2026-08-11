"""Summarize and cluster row-level Microsoft Foundry evaluation results."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize failed and errored Foundry evaluation criteria."
    )
    parser.add_argument("result_file", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _criterion(result: dict[str, Any]) -> str:
    return str(result.get("metric") or result.get("name") or "unknown")


def _failure_kind(result: dict[str, Any]) -> str | None:
    status = str(result.get("status") or "").lower()
    if status in {"error", "errored", "failed"}:
        return "error"
    if result.get("passed") is False:
        return "failure"
    return None


def _cluster(criterion: str, kind: str, reason: str) -> str:
    lowered = reason.lower()
    if kind == "error" or "tool definition" in lowered:
        return "evaluation infrastructure"
    if criterion == "tool_call_accuracy":
        return "tool evaluation"
    if "not answer" in lowered or "does not provide" in lowered:
        return "incomplete answer"
    if "incorrect" in lowered or "wrong" in lowered or "contradict" in lowered:
        return "incorrect answer"
    if "refus" in lowered or "out of scope" in lowered:
        return "off-topic or refusal"
    return "quality or instruction adherence"


def _reason(result: dict[str, Any]) -> str:
    sample_error = (result.get("sample") or {}).get("error") or {}
    return str(
        result.get("reason")
        or result.get("error")
        or sample_error.get("message")
        or "No reason"
    )


def main() -> int:
    args = _arguments()
    payload = json.loads(args.result_file.read_text(encoding="utf-8"))
    run = payload["run"]
    rows: list[dict[str, Any]] = []
    cluster_counts: Counter[str] = Counter()
    criterion_counts: Counter[str] = Counter()

    for item in payload["output_items"]:
        source = item.get("datasource_item", {})
        findings = []
        for result in item.get("results", []):
            criterion = _criterion(result)
            kind = _failure_kind(result)
            if kind is None:
                continue
            reason = _reason(result)
            cluster = _cluster(criterion, kind, reason)
            cluster_counts[cluster] += 1
            criterion_counts[f"{criterion}:{kind}"] += 1
            findings.append(
                {
                    "criterion": criterion,
                    "kind": kind,
                    "score": result.get("score"),
                    "label": result.get("label"),
                    "cluster": cluster,
                    "reason": reason,
                }
            )
        if findings:
            rows.append(
                {
                    "item_id": item.get("id"),
                    "query": source.get("query"),
                    "response": source.get("sample.output_text"),
                    "tool_call_count": len(source.get("sample.tool_calls") or []),
                    "tool_definition_count": len(
                        source.get("sample.tool_definitions") or []
                    ),
                    "findings": findings,
                }
            )

    summary = {
        "eval_id": run.get("eval_id"),
        "run_id": run.get("id"),
        "status": run.get("status"),
        "result_counts": run.get("result_counts"),
        "per_criterion": run.get("per_testing_criteria_results"),
        "failure_clusters": dict(cluster_counts),
        "finding_counts": dict(criterion_counts),
        "rows_with_findings": rows,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(summary, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())