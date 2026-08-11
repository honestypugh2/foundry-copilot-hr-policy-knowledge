"""Evaluate captured Hosted tool calls with an explicit function schema."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.config.azure_identity import verify_azure_cli_identity
from src.evaluation.hr_policy_tool_schema import (
    SEARCH_HR_POLICIES_TOOL_DEFINITION,
    tool_call_evaluator_definition,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ToolCallAccuracyEvaluator over captured Hosted output."
    )
    parser.add_argument("result_file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retrieval-mode", choices=("tool",), default="tool")
    return parser.parse_args()


def _model_configuration() -> tuple[Any, Any]:
    from azure.ai.evaluation import AzureOpenAIModelConfiguration
    from azure.identity import AzureCliCredential

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    if not endpoint or not deployment:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME are required"
        )
    configuration = AzureOpenAIModelConfiguration(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01"),
    )
    return configuration, AzureCliCredential(
        tenant_id=os.environ["EXPECTED_AZURE_TENANT_ID"]
    )


def main() -> int:
    args = _arguments()
    load_dotenv()
    identity = verify_azure_cli_identity(
        expected_tenant_id=os.environ.get("EXPECTED_AZURE_TENANT_ID", ""),
        expected_subscription_id=os.environ.get(
            "EXPECTED_AZURE_SUBSCRIPTION_ID", ""
        ),
        expected_principal_id=os.environ.get("EXPECTED_AZURE_PRINCIPAL_ID", ""),
        token_scope="https://cognitiveservices.azure.com/.default",
    )

    from azure.ai.evaluation import ToolCallAccuracyEvaluator

    model_config, credential = _model_configuration()
    evaluator = ToolCallAccuracyEvaluator(model_config, credential=credential)
    payload = json.loads(args.result_file.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in payload.get("output_items", []):
        source = item.get("datasource_item", {})
        captured_messages = source.get("sample.tool_calls") or []
        function_calls = [
            {
                "type": "tool_call",
                "tool_call_id": content.get("tool_call_id"),
                "name": content.get("name"),
                "arguments": content.get("arguments", {}),
            }
            for message in captured_messages
            for content in message.get("content", [])
            if content.get("type") == "function_call"
        ]
        if not function_calls:
            rows.append(
                {
                    "item_id": item.get("id"),
                    "query": source.get("query"),
                    "status": "error",
                    "error": "No captured function call",
                }
            )
            continue
        try:
            result = evaluator(
                query=source.get("query", ""),
                tool_definitions=[tool_call_evaluator_definition()],
                tool_calls=function_calls,
            )
            evaluator_status = str(result.get("tool_call_accuracy_status") or "")
            if evaluator_status.lower() in {"skipped", "not_applicable"}:
                raise RuntimeError(
                    result.get("tool_call_accuracy_reason")
                    or "Tool call evaluation was skipped"
                )
            rows.append(
                {
                    "item_id": item.get("id"),
                    "query": source.get("query"),
                    "status": "completed",
                    "function_call_count": len(function_calls),
                    "result": result,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "item_id": item.get("id"),
                    "query": source.get("query"),
                    "status": "error",
                    "function_call_count": len(function_calls),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    output = {
        "source_result": str(args.result_file),
        "retrieval_mode": args.retrieval_mode,
        "identity": identity,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "tool_definition": SEARCH_HR_POLICIES_TOOL_DEFINITION,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("completed", "errors")}, indent=2))
    return 1 if output["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
