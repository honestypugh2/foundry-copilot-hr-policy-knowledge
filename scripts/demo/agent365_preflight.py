"""Read-only Agent 365 checks; never grants permissions or sends conversations.

python -m scripts.demo.agent365_preflight --hosted-agent-principal-id <object-id>
Repeat --hosted-agent-principal-id for each hosted identity in this account.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv

OTEL_WRITE_ROLE = "8f71190c-00c8-461d-a63b-f74abde9ba52"
ACCOUNT_API_VERSION = "2026-03-15-preview"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def az_json(*args: str) -> Any:
    result = subprocess.run(
        ["az", *args, "-o", "json"], capture_output=True, text=True, timeout=90
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"az exited {result.returncode}")
    return json.loads(result.stdout)


def collect_checks(account_id: str, hosted_ids: list[str]) -> list[Check]:
    account = az_json(
        "rest", "--method", "GET", "--url",
        f"https://management.azure.com{account_id}?api-version={ACCOUNT_API_VERSION}",
    )
    props = account.get("properties", {})
    checks = [
        Check(
            "Foundry Agent 365 collection",
            "PASS" if props.get("a365LoggingEnabled") is True
            and props.get("a365Status") == "Enabled" else "FAIL",
            f"logging={props.get('a365LoggingEnabled')}, status={props.get('a365Status')}",
        )
    ]
    services = az_json(
        "rest", "--method", "GET", "--url",
        "https://graph.microsoft.com/v1.0/servicePrincipals"
        "?$filter=displayName%20eq%20'Agent365Observability'&$select=id,appRoles",
    )["value"]
    if len(services) != 1:
        checks.append(Check("Agent365Observability", "FAIL", "Expected exactly one service principal"))
        return checks
    service = services[0]
    role_present = any(
        role["id"] == OTEL_WRITE_ROLE and role.get("isEnabled") is True
        for role in service.get("appRoles", [])
    )
    checks.append(Check(
        "Agent365Observability", "PASS" if role_present else "FAIL",
        f"service principal={service['id']}; OtelWrite enabled={role_present}",
    ))
    for principal_id in hosted_ids:
        principal = az_json(
            "rest", "--method", "GET", "--url",
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{principal_id}"
            "?$select=id,appId,displayName",
        )
        assignments = az_json(
            "rest", "--method", "GET", "--url",
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{principal_id}/appRoleAssignments",
        )["value"]
        assigned = any(
            row.get("appRoleId") == OTEL_WRITE_ROLE
            and row.get("resourceId") == service["id"] for row in assignments
        )
        checks.append(Check(
            f"Hosted OtelWrite: {principal['displayName']}",
            "PASS" if assigned else "FAIL",
            f"objectId={principal_id}; appId={principal['appId']}",
        ))
    if not hosted_ids:
        checks.append(Check(
            "Hosted identity coverage", "UNKNOWN",
            "Supply --hosted-agent-principal-id for every hosted agent; no identities checked.",
        ))
    pricing = az_json("security", "pricing", "show", "-n", "AI")
    extensions = {
        row["name"]: str(row.get("isEnabled")).lower() == "true"
        for row in pricing.get("extensions", [])
    }
    checks.append(Check(
        "Defender for AI", "PASS" if pricing.get("pricingTier") == "Standard" else "FAIL",
        f"tier={pricing.get('pricingTier')}",
    ))
    checks.append(Check(
        "Suspicious prompt evidence",
        "PASS" if extensions.get("AIPromptEvidence") else "FAIL",
        "This is not proof of an alert or its Agent 365 attribution.",
    ))
    checks.append(Check(
        "Agent 365 ingestion and security risk visibility", "UNKNOWN",
        "Verify a fresh published-agent session in Agent 365 and Defender. "
        "Configuration checks cannot prove ingestion or backfill old alerts.",
    ))
    return checks


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    project_id = os.getenv("AZURE_AI_PROJECT_RESOURCE_ID", "")
    parser.add_argument(
        "--account-resource-id", default=project_id.split("/projects/")[0],
        help="Foundry account ARM ID; defaults to the parent of AZURE_AI_PROJECT_RESOURCE_ID.",
    )
    parser.add_argument("--hosted-agent-principal-id", action="append", default=[])
    args = parser.parse_args()
    parts = args.account_resource_id.strip("/").split("/")
    if len(parts) != 8 or parts[0].lower() != "subscriptions" or parts[6].lower() != "accounts":
        parser.error("Supply a Microsoft.CognitiveServices account ARM resource ID.")
    if parts[4].lower() != "providers" or parts[5].lower() != "microsoft.cognitiveservices":
        parser.error("Account must be a Microsoft.CognitiveServices resource.")
    try:
        for principal_id in args.hosted_agent_principal_id:
            UUID(principal_id)
        current = az_json("account", "show")
        expected_tenant = os.getenv("EXPECTED_AZURE_TENANT_ID")
        expected_subscription = os.getenv("EXPECTED_AZURE_SUBSCRIPTION_ID")
        if current["id"].lower() != parts[1].lower():
            raise ValueError("Active subscription does not match target account.")
        if expected_subscription and current["id"].lower() != expected_subscription.lower():
            raise ValueError("Active subscription does not match EXPECTED_AZURE_SUBSCRIPTION_ID.")
        if expected_tenant and current["tenantId"].lower() != expected_tenant.lower():
            raise ValueError("Active tenant does not match EXPECTED_AZURE_TENANT_ID.")
        checks = collect_checks(args.account_resource_id, args.hosted_agent_principal_id)
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] Agent 365 preflight: {exc}")
        return 1
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.detail}")
    if any(check.status == "FAIL" for check in checks):
        return 1
    print("Configuration checks passed; end-to-end visibility remains UNVERIFIED.")
    return 2 if any(check.status == "UNKNOWN" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
