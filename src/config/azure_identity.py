"""Fail-closed Azure CLI identity checks for live project operations."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from typing import Any, Callable

from azure.identity import AzureCliCredential
from dotenv import load_dotenv


def _token_claims(token: str) -> dict[str, Any]:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def verify_azure_cli_identity(
    *,
    expected_tenant_id: str,
    expected_subscription_id: str,
    expected_principal_id: str,
    token_scope: str = "https://management.azure.com/.default",
    credential_factory: Callable[..., Any] = AzureCliCredential,
    command_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, str | None]:
    """Verify token tenant/principal and the Azure CLI active subscription."""
    expected = {
        "tenant_id": expected_tenant_id.strip().lower(),
        "subscription_id": expected_subscription_id.strip().lower(),
        "principal_id": expected_principal_id.strip().lower(),
    }
    missing = [name for name, value in expected.items() if not value]
    if missing:
        raise ValueError(f"Missing expected Azure identity values: {', '.join(missing)}")

    credential = credential_factory(tenant_id=expected["tenant_id"])
    claims = _token_claims(credential.get_token(token_scope).token)
    account = command_runner(
        ["az", "account", "show", "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    account_payload = json.loads(account.stdout)
    actual = {
        "tenant_id": str(claims.get("tid") or "").lower(),
        "subscription_id": str(account_payload.get("id") or "").lower(),
        "principal_id": str(claims.get("oid") or "").lower(),
        "user_principal_name": claims.get("upn") or claims.get("unique_name"),
    }
    mismatches = [
        f"{name}: expected {expected[name]}, got {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]
    if mismatches:
        raise RuntimeError("Azure identity preflight failed: " + "; ".join(mismatches))
    return actual


def main() -> int:
    """Verify the active CLI identity against the repository's pinned target."""
    load_dotenv(override=True)
    try:
        actual = verify_azure_cli_identity(
            expected_tenant_id=os.environ.get("EXPECTED_AZURE_TENANT_ID", ""),
            expected_subscription_id=os.environ.get(
                "EXPECTED_AZURE_SUBSCRIPTION_ID", ""
            ),
            expected_principal_id=os.environ.get(
                "EXPECTED_AZURE_PRINCIPAL_ID", ""
            ),
        )
    except Exception as exc:
        print(f"Azure identity preflight failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(actual, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
