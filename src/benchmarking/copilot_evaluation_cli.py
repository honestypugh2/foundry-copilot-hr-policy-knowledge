"""Run and import native Copilot Studio standard-harness evaluations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from azure.identity import DeviceCodeCredential
from dotenv import load_dotenv

from src.benchmarking.copilot_evaluation import (
    attach_copilot_evaluation,
    import_copilot_evaluation,
    import_github_copilot_conversation_evaluation,
    sanitize_native_run,
)
from src.config.azure_identity import verify_azure_cli_identity
from src.copilot_studio.evaluation_service import CopilotStudioEvaluationService


def _required(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"Missing required setting: {name}")
    return value


def _run(args: argparse.Namespace) -> int:
    expected_tenant_id = _required(
        os.getenv("EXPECTED_AZURE_TENANT_ID"), "EXPECTED_AZURE_TENANT_ID"
    )
    expected_principal_id = _required(
        os.getenv("EXPECTED_AZURE_PRINCIPAL_ID"), "EXPECTED_AZURE_PRINCIPAL_ID"
    )
    verify_azure_cli_identity(
        expected_tenant_id=expected_tenant_id,
        expected_subscription_id=_required(
            os.getenv("EXPECTED_AZURE_SUBSCRIPTION_ID"),
            "EXPECTED_AZURE_SUBSCRIPTION_ID",
        ),
        expected_principal_id=expected_principal_id,
    )
    environment_id = _required(
        args.environment_id or os.getenv("COPILOT_STUDIO_ENVIRONMENT_ID"),
        "COPILOT_STUDIO_ENVIRONMENT_ID",
    )
    bot_id = _required(
        args.bot_id or os.getenv("COPILOT_STUDIO_BOT_ID"),
        "COPILOT_STUDIO_BOT_ID",
    )
    client_id = _required(
        args.client_id or os.getenv("POWER_PLATFORM_EVALUATION_CLIENT_ID"),
        "POWER_PLATFORM_EVALUATION_CLIENT_ID",
    )
    credential = DeviceCodeCredential(
        tenant_id=expected_tenant_id,
        client_id=client_id,
    )
    service = CopilotStudioEvaluationService(
        environment_id=environment_id,
        bot_id=bot_id,
        credential=credential,
        expected_tenant_id=expected_tenant_id,
        expected_principal_id=expected_principal_id,
    )
    try:
        test_set, run = service.run_named_test_set(
            test_set_name=args.test_set_name,
            expected_case_count=args.expected_case_count,
            run_name=args.run_name,
            mcs_connection_id=args.mcs_connection_id,
            timeout_seconds=args.timeout_seconds,
        )
    finally:
        service.close()
    artifact = sanitize_native_run(run)
    artifact["resolvedTestSet"] = {
        "id": test_set.get("id"),
        "displayName": test_set.get("displayName"),
        "state": test_set.get("state"),
        "totalTestCases": test_set.get("totalTestCases"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Completed Copilot Studio Evaluation run {run['id']}")
    print(f"Saved sanitized run evidence to {args.output}")
    return 0


def _import(args: argparse.Namespace) -> int:
    artifact = import_copilot_evaluation(
        export_csv_path=args.export_csv,
        cases_path=args.cases,
        specifications_path=args.evaluation_spec,
        native_run_path=args.native_run,
        experiment_id=args.experiment_id,
        dataset_version=args.dataset_version,
        expected_environment_id=args.environment_id,
        expected_bot_id=args.bot_id,
        expected_test_set_id=args.test_set_id,
        allow_nondecisive=args.archive_nondecisive,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    if args.report:
        attach_copilot_evaluation(args.report, args.output)
        print(f"Attached native Evaluation evidence to {args.report}")
    print(f"Saved normalized Evaluation evidence to {args.output}")
    return 0


def _import_conversation(args: argparse.Namespace) -> int:
    artifact = import_github_copilot_conversation_evaluation(
        export_csv_path=args.export_csv,
        cases_path=args.cases,
        specifications_path=args.evaluation_spec,
        experiment_id=args.experiment_id,
        dataset_version=args.dataset_version,
        run_name=args.run_name,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    if args.report:
        attach_copilot_evaluation(args.report, args.output)
        print(f"Attached native Evaluation evidence to {args.report}")
    print(f"Saved normalized Evaluation evidence to {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(
        description="Run or import Copilot Studio native Evaluation evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Trigger an existing test set through the Power Platform API"
    )
    run_parser.add_argument("--test-set-name", required=True)
    run_parser.add_argument("--expected-case-count", type=int, required=True)
    run_parser.add_argument("--run-name", required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--environment-id")
    run_parser.add_argument("--bot-id")
    run_parser.add_argument("--client-id")
    run_parser.add_argument("--mcs-connection-id")
    run_parser.add_argument("--timeout-seconds", type=float, default=900)
    run_parser.set_defaults(handler=_run)

    import_parser = subparsers.add_parser(
        "import", help="Normalize API run details plus the Evaluation UI CSV export"
    )
    import_parser.add_argument("--export-csv", type=Path, required=True)
    import_parser.add_argument("--native-run", type=Path, required=True)
    import_parser.add_argument("--cases", type=Path, required=True)
    import_parser.add_argument("--evaluation-spec", type=Path, required=True)
    import_parser.add_argument("--experiment-id", required=True)
    import_parser.add_argument("--dataset-version", required=True)
    import_parser.add_argument("--output", type=Path, required=True)
    import_parser.add_argument("--report", type=Path)
    import_parser.add_argument("--environment-id", required=True)
    import_parser.add_argument("--bot-id", required=True)
    import_parser.add_argument("--test-set-id", required=True)
    import_parser.add_argument(
        "--archive-nondecisive",
        action="store_true",
        help="Archive Error/Invalid results as release-blocking evidence",
    )
    import_parser.set_defaults(handler=_import)

    conversation_parser = subparsers.add_parser(
        "import-conversation",
        help=(
            "Normalize a GitHub Copilot Harness 'Conversation' CSV export "
            "(single GeneralQuality method, no API run artifact)"
        ),
    )
    conversation_parser.add_argument("--export-csv", type=Path, required=True)
    conversation_parser.add_argument("--cases", type=Path, required=True)
    conversation_parser.add_argument("--evaluation-spec", type=Path, required=True)
    conversation_parser.add_argument("--experiment-id", required=True)
    conversation_parser.add_argument("--dataset-version", required=True)
    conversation_parser.add_argument("--output", type=Path, required=True)
    conversation_parser.add_argument("--report", type=Path)
    conversation_parser.add_argument("--run-name")
    conversation_parser.set_defaults(handler=_import_conversation)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())