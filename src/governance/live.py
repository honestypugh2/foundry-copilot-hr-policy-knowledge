"""Commercial-demo collectors and opt-in inference; no deployment or policy writes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import quote, urlparse
from uuid import UUID

import httpx
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from openai import APIStatusError

from scripts.demo import agent365_preflight, gateway_demo
from src.governance.evidence import Asset, Estate, Evidence, utc_now

PROJECT_ID = re.compile(
    r"/subscriptions/([0-9a-f-]{36})/resourceGroups/([^/]+)/providers/"
    r"Microsoft\.CognitiveServices/accounts/([^/]+)/projects/([^/]+)", re.IGNORECASE,
)


def _az(*args: str) -> object:
    result = subprocess.run(
        ["az", *args, "--output", "json"], capture_output=True, text=True, timeout=90,
    )
    if result.returncode:
        raise RuntimeError(
            f"Azure CLI read '{' '.join(args[:3])}' failed (exit {result.returncode}); "
            "inspect that command with Azure CLI. Raw diagnostic output is not exported."
        )
    return json.loads(result.stdout)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Expected an object from Azure.")
    return {str(key): item for key, item in value.items()}


def _rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError("Expected a list of objects from Azure.")
    return [_object(row) for row in value]


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a nonempty text field from Azure.")
    return value


def _scope(env: Mapping[str, str]) -> tuple[str, str, str]:
    match = PROJECT_ID.fullmatch(env.get("AZURE_AI_PROJECT_RESOURCE_ID", ""))
    if not match:
        raise ValueError("AZURE_AI_PROJECT_RESOURCE_ID must be a Foundry project ARM ID.")
    subscription, group, account, project = match.groups()
    cloud = _object(_az("cloud", "show"))
    if cloud.get("name") != "AzureCloud":
        raise ValueError("Live collectors support Azure Commercial only; cloud parity is not inferred.")
    current = _object(_az("account", "show"))
    expected_subscription = env.get("EXPECTED_AZURE_SUBSCRIPTION_ID", subscription)
    expected_tenant = env.get("EXPECTED_AZURE_TENANT_ID")
    if str(current.get("id", "")).lower() != subscription.lower() or (
        expected_subscription.lower() != subscription.lower()
    ):
        raise ValueError("Active and expected subscription must match the target project.")
    if expected_tenant and str(current.get("tenantId", "")).lower() != expected_tenant.lower():
        raise ValueError("Active tenant does not match EXPECTED_AZURE_TENANT_ID.")
    endpoint = f"https://{account}.services.ai.azure.com/api/projects/{project}"
    return subscription, group, endpoint


def collect_live(
    env: Mapping[str, str] | None = None, hosted_principal_ids: tuple[str, ...] = (),
) -> Estate:
    """Read a single resource group/project; never enumerate other tenants."""
    env = os.environ if env is None else env
    for principal_id in hosted_principal_ids:
        UUID(principal_id)
    subscription, group, endpoint = _scope(env)
    stamp = utc_now()
    resources = _rows(_az(
        "resource", "list", "--resource-group", group, "--subscription", subscription,
        "--query", "[].{id:id,name:name,type:type}",
    ))
    assets = [Asset(
        asset_id=_text(row.get("id")), name=_text(row.get("name")), platform=_text(row.get("type")),
        cloud="Azure Commercial", runtime="Azure resource",
        evidence_kind="live", collected_at=stamp,
        source=f"https://portal.azure.com/#resource{row['id']}",
    ) for row in resources]
    requested_project_id = env["AZURE_AI_PROJECT_RESOURCE_ID"]
    project_id = next(
        (asset.asset_id for asset in assets if asset.asset_id.lower() == requested_project_id.lower()),
        requested_project_id,
    )
    if not any(asset.asset_id.lower() == project_id.lower() for asset in assets):
        assets.append(Asset(
            asset_id=project_id, name=project_id.rsplit("/", 1)[-1], platform="Foundry",
            cloud="Azure Commercial", runtime="Project collection scope",
            evidence_kind="unverified", collected_at=stamp, source=endpoint,
        ))
    rows = [Evidence(
        asset_id=asset.asset_id, category="inventory",
        observation="Resource metadata only; owner and agent identity not resolved.",
        status="observed" if asset.evidence_kind == "live" else "unknown",
        evidence_kind=asset.evidence_kind, source=asset.source, collected_at=stamp,
    ) for asset in assets]
    try:
        with DefaultAzureCredential() as credential, AIProjectClient(
            endpoint=endpoint, credential=credential,
        ) as client:
            for agent in client.agents.list():
                asset_id = f"{project_id}/agents/{agent.name}"
                assets.append(Asset(
                    asset_id=asset_id, name=agent.name, platform="Foundry",
                    cloud="Azure Commercial", runtime="Foundry agent (version not inspected)",
                    source=endpoint, evidence_kind="live", collected_at=stamp,
                ))
                rows.append(Evidence(
                    asset_id=asset_id, category="inventory", observation=(
                        "Agent definition exists; publication, identity and telemetry not verified."
                    ), status="observed", evidence_kind="live", source=endpoint, collected_at=stamp,
                ))
    except (AzureError, ValueError) as exc:
        rows.append(_unavailable(project_id, "Agent inventory read", type(exc).__name__, endpoint))

    # Reuse the existing configuration diagnostic, without granting any permissions.
    try:
        checks = agent365_preflight.collect_checks(
            project_id.rsplit("/", 2)[0], list(hosted_principal_ids),
        )
        for check in checks:
            rows.append(Evidence(
                asset_id=project_id, category="control" if check.status != "UNKNOWN" else "visibility",
                observation=f"{check.name}: {check.status}; configuration only, not ingestion.",
                status={"PASS": "observed", "FAIL": "attention", "UNKNOWN": "unknown"}[check.status],
                evidence_kind="unverified" if check.status == "UNKNOWN" else "live",
                source="ARM / Graph / Defender configuration", collected_at=utc_now(),
            ))
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        rows.append(_unavailable(
            project_id, "Agent 365 configuration read", type(exc).__name__, endpoint,
        ))
    rows.extend(_gateway_logs(assets))
    account_id = project_id.rsplit("/", 2)[0]
    # Alert metadata is account-scoped evidence, never an inferred agent risk.
    if any(asset.asset_id.lower() == account_id.lower() for asset in assets):
        account_id = next(a.asset_id for a in assets if a.asset_id.lower() == account_id.lower())
        rows.extend(_defender_alerts(subscription, group, account_id))
    for asset in tuple(assets):
        rows.append(Evidence(
            asset_id=asset.asset_id, category="security", status="unknown",
            evidence_kind="unverified", source="Security platforms (no risk collector)",
            collected_at=stamp,
            observation="No verified agent-attributed risk feed; do not interpret as zero risks.",
        ))
    return Estate(assets=tuple(assets), evidence=tuple(rows))


def _defender_alerts(subscription: str, group: str, account_id: str) -> list[Evidence]:
    source = f"https://portal.azure.com/#resource{account_id}"
    try:
        alerts = _rows(_az(
            "security", "alert", "list", "--resource-group", group, "--subscription", subscription,
            "--query",
            "[].{id:id,status:status,severity:severity,time:timeGeneratedUtc,"
            "resources:resourceIdentifiers[].azureResourceId}",
        ))
        rows = []
        for alert in alerts:
            resources = alert.get("resources") or []
            if not isinstance(resources, list):
                raise ValueError("Invalid alert resource identifiers.")
            if str(alert.get("status", "")).lower() != "active" or not any(
                isinstance(resource, str) and (
                    resource.lower() == account_id.lower()
                    or resource.lower().startswith(account_id.lower() + "/")
                ) for resource in resources
            ):
                continue
            severity = alert.get("severity")
            if severity not in ("High", "Medium", "Low", "Informational"):
                severity = "Unknown"
            event_at = alert.get("time")
            rows.append(Evidence(
                asset_id=account_id, category="security", status="attention",
                evidence_kind="live", collected_at=utc_now(),
                event_at=(
                    datetime.fromisoformat(_text(event_at).replace("Z", "+00:00"))
                    if event_at else None
                ),
                observation=(
                    f"Active Defender for Cloud source alert ({severity}); "
                    "account scope only, not Agent 365 or agent-risk attribution."
                ),
                source=f"https://portal.azure.com/#resource{alert['id']}",
                signal_count=1,
            ))
        if not rows:
            rows.append(Evidence(
                asset_id=account_id, category="security", status="observed",
                evidence_kind="live", collected_at=utc_now(), source=source, signal_count=0,
                observation=(
                    "No account-matched active alerts returned; missing/other feeds and "
                    "unresolved identity attribution are not a zero-risk assertion."
                ),
            ))
        return rows
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        return [_unavailable(account_id, "Defender alert metadata read", type(exc).__name__, source)]


def _gateway_logs(assets: list[Asset]) -> list[Evidence]:
    gateways = [a for a in assets if a.platform.lower() == "microsoft.apimanagement/service"]
    workspaces = [a for a in assets if a.platform.lower() == "microsoft.operationalinsights/workspaces"]
    rows = []
    for gateway in gateways:
        if len(workspaces) != 1:
            rows.append(_unavailable(
                gateway.asset_id, "Gateway log collection", "workspace scope ambiguous or absent",
                gateway.source,
            ))
            continue
        try:
            workspace = _az(
                "monitor", "log-analytics", "workspace", "show", "--ids", workspaces[0].asset_id,
                "--query", "customerId",
            )
            UUID(str(workspace))
            resource_id = gateway.asset_id.replace("'", "''")
            query = (
                "ApiManagementGatewayLogs | where TimeGenerated > ago(1h) "
                f"| where _ResourceId =~ '{resource_id}' "
                "| summarize RequestCount=count() by ResponseCode=tostring(ResponseCode)"
            )
            result = _rows(_az(
                "monitor", "log-analytics", "query", "--workspace", str(workspace),
                "--analytics-query", query,
            ))
            for row in result:
                code, count = int(_text(row.get("ResponseCode"))), _number(row.get("RequestCount"))
                if count is None:
                    raise ValueError("Invalid gateway request count.")
                rows.append(Evidence(
                    asset_id=gateway.asset_id, category="usage", status="observed",
                    observation="Gateway requests by status in the last hour; not agent attribution.",
                    evidence_kind="live", source=workspaces[0].source, collected_at=utc_now(),
                    http_status=code, request_count=count,
                ))
            if not result:
                rows.append(Evidence(
                    asset_id=gateway.asset_id, category="visibility", status="unknown",
                    evidence_kind="unverified", source=workspaces[0].source, collected_at=utc_now(),
                    observation="No gateway log rows in the last hour; ingestion is not established.",
                ))
        except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
            rows.append(_unavailable(
                gateway.asset_id, "Gateway log query", type(exc).__name__, workspaces[0].source,
            ))
    return rows


def _unavailable(asset_id: str, operation: str, error: str, source: str) -> Evidence:
    return Evidence(
        asset_id=asset_id, category="visibility", status="error", evidence_kind="unavailable",
        observation=f"{operation} failed ({error}); coverage unavailable. Retry in the source tool.",
        source=source, collected_at=utc_now(),
    )


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def response_evidence(
    response: httpx.Response, *, asset_id: str, consumer: str, latency_ms: float,
) -> Evidence:
    """Extract an allowlist of metadata; omit prompts, completions, bodies and keys."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    body = _object(body) if isinstance(body, dict) else {}
    usage = body.get("usage")
    usage = _object(usage) if isinstance(usage, dict) else {}
    error = body.get("error")
    error = _object(error) if isinstance(error, dict) else {}
    choices = body.get("choices")
    choices = choices if isinstance(choices, list) else []
    filtered = error.get("code") == "content_filter" or any(
        isinstance(choice, dict) and choice.get("finish_reason") == "content_filter"
        for choice in choices
    )
    if filtered:
        outcome = "Content-filter block observed; Defender/Agent 365 risk not established."
    elif response.status_code == 429:
        outcome = "Rate limited; the response alone does not identify which quota caused it."
    elif 200 <= response.status_code < 300:
        outcome = "Request accepted; not proof of telemetry ingestion or a useful answer."
    else:
        outcome = "Request failed; inspect the source service."
    remaining = response.headers.get("x-ratelimit-remaining-tokens", "")
    correlation = response.headers.get("apim-request-id") or response.headers.get("x-request-id")
    if correlation and not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", correlation):
        correlation = None
    return Evidence(
        asset_id=asset_id, category="control" if filtered else "usage",
        observation=f"{consumer}: {outcome}", status=(
            "observed" if 200 <= response.status_code < 300 and not filtered else "attention"
        ), evidence_kind="live", source="Invocation response metadata", collected_at=utc_now(),
        http_status=response.status_code, total_tokens=_number(usage.get("total_tokens")),
        remaining_tokens=int(remaining) if remaining.isascii() and remaining.isdigit() else None,
        latency_ms=latency_ms, request_count=1, correlation_id=correlation,
    )


def invoke_gateway(
    consumer: str = "asset-agent", *, allow_inference: bool = False,
    jailbreak: bool = False, env: Mapping[str, str] | None = None,
) -> Evidence:
    if not allow_inference:
        raise PermissionError("Paid inference requires allow_inference=True.")
    if consumer not in gateway_demo.KEY_ENV:
        raise ValueError("Unknown consumer.")
    env = os.environ if env is None else env
    _scope(env)
    base = env.get("APIM_GATEWAY_URL", "").rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(
        ".azure-api.net"
    ) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError("APIM_GATEWAY_URL must be an HTTPS Azure APIM gateway origin.")
    key = env.get(gateway_demo.KEY_ENV[consumer])
    if not key:
        raise ValueError(f"Missing {gateway_demo.KEY_ENV[consumer]}.")
    deployment = quote(env.get("APIM_DEPLOYMENT_NAME", "gpt-5-mini"), safe="")
    version = quote(env.get("APIM_API_VERSION", "2024-10-21"), safe="")
    url = f"{base}/openai/deployments/{deployment}/chat/completions?api-version={version}"
    with httpx.Client(timeout=60) as client:
        response, latency = gateway_demo.call(
            client, url, key, consumer,
            gateway_demo.JAILBREAK if jailbreak else gateway_demo.DEFAULT_QUESTION, 400,
        )
    return response_evidence(
        response, asset_id="gateway", consumer=consumer, latency_ms=latency,
    )


def invoke_agent(
    agent_name: str, *, hosted: bool = False, allow_inference: bool = False,
    jailbreak: bool = False, env: Mapping[str, str] | None = None,
) -> Evidence:
    """Invoke an existing agent only; no initialization, creation or local fallback."""
    if not allow_inference:
        raise PermissionError("Paid inference requires allow_inference=True.")
    env = os.environ if env is None else env
    _, _, endpoint = _scope(env)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", agent_name):
        raise ValueError("Invalid agent name.")
    prompt = gateway_demo.JAILBREAK if jailbreak else gateway_demo.DEFAULT_QUESTION
    with DefaultAzureCredential() as credential:
        if hosted:
            url = f"{endpoint}/agents/{agent_name}/endpoint/protocols/openai/responses"
            token = credential.get_token("https://ai.azure.com/.default").token
            start = time.perf_counter()
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    url, headers={"Authorization": f"Bearer {token}"}, json={"input": prompt},
                )
            latency = (time.perf_counter() - start) * 1000
        else:
            with AIProjectClient(endpoint=endpoint, credential=credential) as project:
                with project.get_openai_client() as client:
                    start = time.perf_counter()
                    try:
                        raw = client.responses.with_raw_response.create(
                            input=prompt,
                            extra_body={
                                "agent_reference": {"name": agent_name, "type": "agent_reference"},
                            },
                        )
                        response = raw.http_response
                    except APIStatusError as exc:
                        response = exc.response
                    latency = (time.perf_counter() - start) * 1000
    return response_evidence(
        response, asset_id=agent_name, consumer=agent_name, latency_ms=latency,
    )
