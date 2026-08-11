"""Stable OpenAI function schema used by HR policy process evaluators."""

from __future__ import annotations

from typing import Any

SEARCH_HR_POLICIES_TOOL_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_hr_policies",
        "description": (
            "Search the HR policy knowledge base for relevant policies, "
            "procedures, and guidelines. Returns excerpts with policy numbers, "
            "titles, and source documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The HR question or policy topic to search for.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def tool_call_evaluator_definition() -> dict[str, Any]:
    """Return the flattened function schema required by Azure AI Evaluation."""
    return dict(SEARCH_HR_POLICIES_TOOL_DEFINITION["function"])
