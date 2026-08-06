"""Lossless normalization of Knowledge Base activity records."""

from __future__ import annotations

from typing import Any

from src.benchmarking.models import ActivityRecord


def _alias(raw: dict[str, Any], camel: str, snake: str) -> dict[str, Any]:
    normalized = dict(raw)
    if camel not in normalized and snake in normalized:
        normalized[camel] = normalized.pop(snake)
    return normalized


def parse_activity(activity: list[Any] | None) -> list[ActivityRecord]:
    """Parse object records while preserving provider fields and unknown types."""
    records: list[ActivityRecord] = []
    for item in activity or []:
        if not isinstance(item, dict):
            continue
        normalized = _alias(item, "elapsedMs", "elapsed_ms")
        normalized = _alias(normalized, "inputTokens", "input_tokens")
        normalized = _alias(normalized, "outputTokens", "output_tokens")
        normalized = _alias(normalized, "reasoningTokens", "reasoning_tokens")
        records.append(ActivityRecord.model_validate(normalized))
    return records


def summarize_activity(records: list[ActivityRecord]) -> dict[str, dict[str, float]]:
    """Group record counts and tokens without adding parallel elapsed times."""
    summary: dict[str, dict[str, float]] = {}
    for record in records:
        raw = record.model_dump(by_alias=True, exclude_none=True)
        bucket = summary.setdefault(
            record.type,
            {
                "records": 0.0,
                "input_tokens": 0.0,
                "output_tokens": 0.0,
                "reasoning_tokens": 0.0,
            },
        )
        bucket["records"] += 1
        bucket["input_tokens"] += float(raw.get("inputTokens", 0))
        bucket["output_tokens"] += float(raw.get("outputTokens", 0))
        bucket["reasoning_tokens"] += float(raw.get("reasoningTokens", 0))
    return summary