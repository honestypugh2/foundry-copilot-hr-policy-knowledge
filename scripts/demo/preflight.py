"""Demo preflight: prints PASS/FAIL for each dependency. Exit 1 if any check fails.

    python -m scripts.demo.preflight
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
RG = "rg-hr-policy-kb-hr-demo"
BACKEND = "https://ca-backend-zptc7utdm2gis.nicedune-3f634c43.eastus2.azurecontainerapps.io"
results: list[bool] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def az(*args: str) -> str:
    return subprocess.run(["az", *args], capture_output=True, text=True, timeout=60).stdout.strip()


def main() -> int:
    load_dotenv(ROOT / ".env")

    expected = os.getenv("EXPECTED_AZURE_SUBSCRIPTION_ID", "")
    current = az("account", "show", "--query", "id", "-o", "tsv")
    check("az account = demo subscription", bool(current) and current == expected, current[:8] + "...")

    try:
        r = httpx.get(f"{BACKEND}/api/health", timeout=30)
        check("backend /api/health", r.status_code == 200, f"HTTP {r.status_code}")
    except httpx.HTTPError as exc:
        check("backend /api/health", False, str(exc)[:80])

    p = subprocess.run(
        [sys.executable, "-m", "src.agents.create_foundry_agent", "--verify-only"],
        capture_output=True, text=True, cwd=ROOT, timeout=120,
    )
    check("HRPolicyAgent / KB verify-only", p.returncode == 0, "see create_foundry_agent --verify-only" if p.returncode else "")

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    index = os.getenv("AZURE_SEARCH_INDEX_NAME", "hr-policy-index")
    try:
        key = os.getenv("AZURE_SEARCH_API_KEY")
        headers = {"api-key": key} if key else {
            "Authorization": "Bearer " + az("account", "get-access-token", "--resource", "https://search.azure.com", "--query", "accessToken", "-o", "tsv")
        }
        r = httpx.get(f"{endpoint}/indexes('{index}')/docs/$count?api-version=2024-07-01", headers=headers, timeout=30)
        count = int(r.text.lstrip("\ufeff").strip()) if r.status_code == 200 else 0
        check(f"search index {index} doc count > 0", count > 0, f"{count} docs" if r.status_code == 200 else f"HTTP {r.status_code}")
    except (httpx.HTTPError, ValueError) as exc:
        check(f"search index {index} doc count > 0", False, str(exc)[:80])

    base = os.getenv("APIM_GATEWAY_URL", "").rstrip("/")
    dep = os.getenv("APIM_DEPLOYMENT_NAME", "gpt-5-mini")
    ver = os.getenv("APIM_API_VERSION", "2024-10-21")
    for label, env in (("asset-agent", "APIM_KEY_ASSET_AGENT"), ("partner-app", "APIM_KEY_PARTNER_APP")):
        key = os.getenv(env, "")
        if not (base and key):
            check(f"APIM gateway ({label})", False, f"missing {env}")
            continue
        try:
            r = httpx.post(
                f"{base}/openai/deployments/{dep}/chat/completions?api-version={ver}",
                headers={"api-key": key, "x-agent-name": label},
                json={"messages": [{"role": "user", "content": "ping"}], "max_completion_tokens": 50},
                timeout=60,
            )
            check(f"APIM gateway ({label})", r.status_code in (200, 429), f"HTTP {r.status_code}")
        except httpx.HTTPError as exc:
            check(f"APIM gateway ({label})", False, str(exc)[:80])

    check("App Insights connection string present", bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")))

    print("\nOVERALL:", "PASS" if all(results) else "FAIL")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
