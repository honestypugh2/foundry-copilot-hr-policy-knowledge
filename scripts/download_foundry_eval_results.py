"""Download Foundry evaluation output items with verified Azure CLI identity."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

from src.config.azure_identity import verify_azure_cli_identity


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a Foundry evaluation run and its output items."
    )
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--principal-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    actual_identity = verify_azure_cli_identity(
        expected_tenant_id=args.tenant_id,
        expected_subscription_id=args.subscription_id,
        expected_principal_id=args.principal_id,
        token_scope="https://ai.azure.com/.default",
    )
    credential = AzureCliCredential(tenant_id=args.tenant_id)

    project_client = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=credential,
    )
    client = project_client.get_openai_client()
    run = client.evals.runs.retrieve(run_id=args.run_id, eval_id=args.eval_id)
    output_items = list(
        client.evals.runs.output_items.list(
            run_id=args.run_id,
            eval_id=args.eval_id,
        )
    )
    payload = {
        "identity": actual_identity,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "run": run.model_dump(mode="json"),
        "output_items": [item.model_dump(mode="json") for item in output_items],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": actual_identity,
                "status": payload["run"].get("status"),
                "output_items": len(output_items),
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())