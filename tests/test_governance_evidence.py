from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from azure.core.exceptions import HttpResponseError
from openai import BadRequestError
from pydantic import ValidationError

from scripts.demo import governance_demo
from src.governance import live
from src.governance.evidence import (
    Asset,
    Estate,
    Evidence,
    coverage,
    export_estate,
    load_snapshot,
    markdown_table,
    overview,
    synthetic_estate,
)

SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
TENANT = "00000000-0000-0000-0000-000000000002"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/pwwdemo-tests"
ACCOUNT = f"{GROUP}/providers/Microsoft.CognitiveServices/accounts/pwwdemo-tests"
PROJECT = f"{ACCOUNT}/projects/pwwdemo-tests"
WORKSPACE = f"{GROUP}/providers/Microsoft.OperationalInsights/workspaces/pwwdemo-tests"
GATEWAY = f"{GROUP}/providers/Microsoft.ApiManagement/service/pwwdemo-tests"
ENV = {
    "AZURE_AI_PROJECT_RESOURCE_ID": PROJECT,
    "EXPECTED_AZURE_TENANT_ID": TENANT,
    "APIM_GATEWAY_URL": "https://pwwdemo-tests.azure-api.net",
    "APIM_KEY_ASSET_AGENT": "synthetic-asset-secret",
    "APIM_KEY_PARTNER_APP": "synthetic-partner-secret",
}


@pytest.fixture
def azure(monkeypatch):
    commands = []
    settings = {"cloud": "AzureCloud", "subscription": SUBSCRIPTION, "tenant": TENANT}

    def az(*args):
        commands.append(args)
        if args[:2] == ("cloud", "show"):
            return {"name": settings["cloud"]}
        if args[:2] == ("account", "show"):
            return {"id": settings["subscription"], "tenantId": settings["tenant"]}
        if args[:2] == ("resource", "list"):
            return [{"id": PROJECT, "name": "pwwdemo-tests", "type": "Foundry"}]
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(live, "_az", az)
    monkeypatch.setattr(live, "DefaultAzureCredential", MagicMock())
    project = MagicMock()
    project.__enter__.return_value = project
    project.agents.list.return_value = [SimpleNamespace(name="pwwdemo-agent")]
    monkeypatch.setattr(live, "AIProjectClient", MagicMock(return_value=project))
    monkeypatch.setattr(
        live.agent365_preflight, "collect_checks",
        lambda *args: [
            live.agent365_preflight.Check("Collection", "PASS", "secret must not be exported"),
            live.agent365_preflight.Check("Ingestion", "UNKNOWN", "Not verified"),
        ],
    )
    return commands, settings, project


def test_synthetic_data_never_claims_tenant_evidence():
    estate = synthetic_estate()
    assert all(asset.evidence_kind == "synthetic" for asset in estate.assets)
    assert all(asset.name.startswith("pwwdemo") for asset in estate.assets)
    assert coverage(estate)["live"] == 0
    assert coverage(estate)["unverified"] > 0
    assert all("not a zero-risk" in row["security"] for row in overview(estate))
    assert "unavailable" in estate.model_dump_json()


def test_evidence_rejects_false_certainty_and_invalid_numbers():
    row = synthetic_estate().evidence[0].model_dump()
    with pytest.raises(ValidationError, match="cannot assert"):
        Evidence(**{**row, "evidence_kind": "unverified"})
    with pytest.raises(ValidationError):
        Evidence(**{**row, "total_tokens": -1})
    with pytest.raises(ValidationError):
        Evidence(**{**row, "collected_at": "2026-10-26T12:00:00"})
    with pytest.raises(ValidationError):
        Evidence(**{**row, "api_key": "not allowed"})


def test_estate_enforces_unique_assets_and_referential_integrity():
    estate = synthetic_estate()
    with pytest.raises(ValidationError, match="unique"):
        Estate(assets=estate.assets + estate.assets, evidence=())
    with pytest.raises(ValidationError, match="reference"):
        Estate(assets=(), evidence=estate.evidence)


def test_snapshot_preserves_provenance_and_time(tmp_path):
    estate = synthetic_estate()
    live_asset = estate.assets[0].model_copy(update={"evidence_kind": "live"})
    live_row = estate.evidence[0].model_copy(update={"evidence_kind": "live"})
    mixed = Estate(assets=(live_asset, *estate.assets[1:]), evidence=(live_row, *estate.evidence[1:]))
    path, _ = export_estate(mixed, tmp_path / "export")
    snapshot = load_snapshot(path)
    assert snapshot.assets[0].evidence_kind == "snapshot"
    assert snapshot.evidence[0].evidence_kind == "snapshot"
    assert snapshot.evidence[1].evidence_kind == "synthetic"
    assert snapshot.evidence[-1].evidence_kind == "unavailable"
    assert snapshot.assets[0].collected_at == live_asset.collected_at
    assert snapshot.assets[0].source == live_asset.source


def test_export_does_not_overwrite_or_hide_unknowns(tmp_path):
    estate = synthetic_estate()
    paths = export_estate(estate, tmp_path)
    assert all(path.exists() for path in paths)
    assert Estate.model_validate_json(paths[0].read_text()) == estate
    with pytest.raises(FileExistsError):
        export_estate(estate, tmp_path)
    assert json.loads(paths[0].read_text())["evidence"][-1]["status"] == "unknown"


def test_csv_formula_and_html_cells_are_escaped(tmp_path):
    estate = synthetic_estate()
    asset = Asset(**{**estate.assets[0].model_dump(), "name": "=1+1"})
    _, path = export_estate(Estate(assets=(asset,), evidence=()), tmp_path)
    assert "'=1+1" in path.read_text()
    table = markdown_table([{"name": "<script>bad()</script>|extra\nrow"}])
    assert "<script>" not in table
    assert "&#124;" in table
    assert "No evidence" in markdown_table([])


@pytest.mark.parametrize("code,body,expected", [
    (200, {"usage": {"total_tokens": 10}}, "Request accepted"),
    (200, {"choices": [{"finish_reason": "content_filter"}]}, "Content-filter block"),
    (400, {"error": {"code": "content_filter"}}, "Content-filter block"),
    (400, {"error": {"code": "invalid_request"}}, "Request failed"),
    (429, {}, "Rate limited"),
    (401, {}, "Request failed"),
    (500, ["malformed"], "Request failed"),
])
def test_response_normalization(code, body, expected):
    response = httpx.Response(
        code, json=body, headers={
            "x-ratelimit-remaining-tokens": "123",
            "apim-request-id": "synthetic-correlation-id",
            "api-key": "must-not-export",
        },
    )
    row = live.response_evidence(response, asset_id="gateway", consumer="asset-agent", latency_ms=1)
    assert expected in row.observation
    assert row.http_status == code
    assert row.remaining_tokens == 123
    assert row.correlation_id == "synthetic-correlation-id"
    assert "must-not-export" not in row.model_dump_json()
    assert "prompt" not in row.model_dump_json()


def test_non_json_and_invalid_usage_stay_unknown():
    row = live.response_evidence(
        httpx.Response(502, text="sensitive-body", headers={"x-ratelimit-remaining-tokens": "-2"}),
        asset_id="gateway", consumer="asset-agent", latency_ms=1,
    )
    assert row.total_tokens is None and row.remaining_tokens is None
    assert "sensitive-body" not in row.model_dump_json()
    row = live.response_evidence(
        httpx.Response(200, json={"usage": {"total_tokens": True}}),
        asset_id="gateway", consumer="asset-agent", latency_ms=1,
    )
    assert row.total_tokens is None


@pytest.mark.parametrize("function,args", [
    (live.invoke_gateway, ()), (live.invoke_agent, ("pwwdemo-agent",)),
])
def test_inference_is_denied_before_any_credentials_or_network(monkeypatch, function, args):
    az = MagicMock(side_effect=AssertionError("must not call Azure"))
    monkeypatch.setattr(live, "_az", az)
    with pytest.raises(PermissionError, match="allow_inference"):
        function(*args, env=ENV)
    az.assert_not_called()


@pytest.mark.parametrize("setting,value", [
    ("cloud", "AzureUSGovernment"), ("tenant", "wrong"), ("subscription", "wrong"),
])
def test_context_mismatch_stops_collection_before_resource_reads(azure, setting, value):
    commands, settings, project = azure
    settings[setting] = value
    with pytest.raises(ValueError):
        live.collect_live(ENV)
    assert not any(command[:2] == ("resource", "list") for command in commands)
    project.agents.list.assert_not_called()


def test_live_collection_is_scoped_and_has_no_risk_success_fallback(azure):
    commands, _, project = azure
    estate = live.collect_live(ENV)
    assert any(asset.name == "pwwdemo-agent" for asset in estate.assets)
    assert all(asset.owner == "Unassigned" for asset in estate.assets)
    assert any(row.category == "security" and row.status == "unknown" for row in estate.evidence)
    assert "secret must not" not in estate.model_dump_json()
    assert any("--resource-group" in command and "pwwdemo-tests" in command for command in commands)
    assert all(not {"create", "update", "delete", "POST", "PUT", "PATCH"} & set(c) for c in commands)
    project.agents.list.assert_called_once_with()


def test_collector_retains_partial_inventory_and_exposes_unavailable_reads(azure, monkeypatch):
    _, _, project = azure
    project.agents.list.side_effect = HttpResponseError("sensitive error text")
    monkeypatch.setattr(
        live.agent365_preflight, "collect_checks",
        MagicMock(side_effect=RuntimeError("sensitive Graph diagnostic")),
    )
    estate = live.collect_live(ENV)
    assert len(estate.assets) == 1
    assert len([row for row in estate.evidence if row.status == "error"]) == 2
    assert "sensitive" not in estate.model_dump_json()


@pytest.mark.parametrize("consumer,key_name", [
    ("asset-agent", "APIM_KEY_ASSET_AGENT"), ("partner-app", "APIM_KEY_PARTNER_APP"),
])
def test_gateway_reuses_existing_call_without_exporting_bodies(azure, monkeypatch, consumer, key_name):
    real_client = httpx.Client

    def handler(request):
        assert request.headers["api-key"] == ENV[key_name]
        assert request.headers["x-agent-name"] == consumer
        assert request.url.params["api-version"] == "2024-10-21"
        return httpx.Response(200, json={
            "usage": {"total_tokens": 12},
            "choices": [{"message": {"content": "private completion"}}],
        })

    monkeypatch.setattr(
        live.httpx, "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    row = live.invoke_gateway(consumer, allow_inference=True, env=ENV)
    assert row.total_tokens == 12
    assert "private completion" not in row.model_dump_json()
    assert "secret" not in row.model_dump_json()


@pytest.mark.parametrize("url", [
    "http://pwwdemo-tests.azure-api.net", "https://untrusted.example",
    "https://user:password@pwwdemo-tests.azure-api.net",
    "https://pwwdemo-tests.azure-api.net/path", "https://pwwdemo-tests.azure-api.net?secret=x",
])
def test_gateway_rejects_unsafe_key_destinations(azure, url):
    with pytest.raises(ValueError, match="origin"):
        live.invoke_gateway(allow_inference=True, env={**ENV, "APIM_GATEWAY_URL": url})


def test_existing_prompt_invocation_has_no_provision_or_fallback(azure):
    _, _, project = azure
    client = project.get_openai_client.return_value.__enter__.return_value
    client.responses.with_raw_response.create.return_value.http_response = httpx.Response(
        200, json={"usage": {"total_tokens": 5}},
    )
    row = live.invoke_agent("HRPolicyAgent", allow_inference=True, env=ENV)
    assert row.total_tokens == 5
    kwargs = client.responses.with_raw_response.create.call_args.kwargs
    assert kwargs["extra_body"]["agent_reference"]["name"] == "HRPolicyAgent"
    project.agents.create.assert_not_called()


def test_prompt_filter_exception_becomes_metadata_not_an_alert(azure):
    _, _, project = azure
    client = project.get_openai_client.return_value.__enter__.return_value
    response = httpx.Response(
        400, json={"error": {"code": "content_filter"}},
        request=httpx.Request("POST", "https://example.test/responses"),
    )
    client.responses.with_raw_response.create.side_effect = BadRequestError(
        "blocked", response=response, body=response.json(),
    )
    row = live.invoke_agent("HRPolicyAgent", allow_inference=True, jailbreak=True, env=ENV)
    assert row.http_status == 400
    assert "risk not established" in row.observation


def test_hosted_agent_uses_responses_endpoint_and_identity(azure, monkeypatch):
    real_client = httpx.Client
    credential = live.DefaultAzureCredential.return_value.__enter__.return_value
    credential.get_token.return_value.token = "synthetic-token"

    def handler(request):
        assert request.url.path.endswith("/agents/hr-policy-agent/endpoint/protocols/openai/responses")
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        return httpx.Response(200, json={"usage": {"total_tokens": 7}})

    monkeypatch.setattr(
        live.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    row = live.invoke_agent("hr-policy-agent", hosted=True, allow_inference=True, env=ENV)
    assert row.total_tokens == 7
    assert "synthetic-token" not in row.model_dump_json()
    credential.get_token.assert_called_once_with("https://ai.azure.com/.default")


@pytest.mark.parametrize("result,expected_status", [
    ([{"ResponseCode": "429", "RequestCount": 3}], "observed"),
    ([], "unknown"),
    ([{"ResponseCode": "429", "RequestCount": -1}], "error"),
])
def test_gateway_logs_are_aggregated_scoped_and_missing_is_not_zero(monkeypatch, result, expected_status):
    template = synthetic_estate().assets[0].model_dump()
    assets = [
        Asset(**{**template, "asset_id": GATEWAY, "platform": "Microsoft.ApiManagement/service"}),
        Asset(**{**template, "asset_id": WORKSPACE, "platform": "Microsoft.OperationalInsights/workspaces"}),
    ]
    commands = []

    def az(*args):
        commands.append(args)
        return SUBSCRIPTION if "show" in args else result

    monkeypatch.setattr(live, "_az", az)
    rows = live._gateway_logs(assets)
    assert rows[0].status == expected_status
    assert GATEWAY in commands[1][-1]
    assert "summarize RequestCount=count()" in commands[1][-1]
    assert "ago(1h)" in commands[1][-1]
    assert "POST" not in str(commands)


def test_defender_source_alerts_are_scoped_not_attributed_to_agents(monkeypatch):
    alerts = [
        {"id": "/synthetic-alert", "status": "Active", "severity": "Medium",
         "time": "2026-10-26T12:00:00Z", "resources": [ACCOUNT]},
        {"id": "/resolved", "status": "Resolved", "severity": "High", "resources": [ACCOUNT]},
        {"id": "/other-account", "status": "Active", "severity": "High", "resources": ["/other"]},
    ]
    az = MagicMock(return_value=alerts)
    monkeypatch.setattr(live, "_az", az)
    rows = live._defender_alerts(SUBSCRIPTION, "pwwdemo-tests", ACCOUNT)
    assert len(rows) == 1 and rows[0].signal_count == 1
    assert rows[0].asset_id == ACCOUNT
    assert rows[0].event_at.isoformat() == "2026-10-26T12:00:00+00:00"
    assert "not Agent 365" in rows[0].observation
    assert "resourceIdentifiers[].azureResourceId" in az.call_args.args[-1]
    assert "--resource-group" in az.call_args.args


def test_no_source_alerts_is_not_zero_risk(monkeypatch):
    monkeypatch.setattr(live, "_az", MagicMock(return_value=[]))
    row = live._defender_alerts(SUBSCRIPTION, "pwwdemo-tests", ACCOUNT)[0]
    assert row.signal_count == 0
    assert "not a zero-risk" in row.observation
    monkeypatch.setattr(live, "_az", MagicMock(side_effect=RuntimeError("secret")))
    row = live._defender_alerts(SUBSCRIPTION, "pwwdemo-tests", ACCOUNT)[0]
    assert row.status == "error" and row.signal_count is None
    assert "secret" not in row.model_dump_json()


def test_cli_defaults_to_synthetic_and_returns_unknown_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(governance_demo, "collect_live", MagicMock(side_effect=AssertionError))
    assert governance_demo.main([]) == 2
    output = capsys.readouterr().out
    assert "synthetic" in output and "UNKNOWN" in output
    assert governance_demo.main(["--snapshot", "/nonexistent/snapshot.json"]) == 1


@pytest.mark.parametrize("name", sorted(
    path.name for path in (Path(__file__).resolve().parents[1] / "notebooks/governance").glob("*.ipynb")
))
def test_notebook_schema_and_offline_execution(name):
    nbformat = pytest.importorskip("nbformat", reason="Install the notebooks extra for execution tests.")
    nbclient = pytest.importorskip("nbclient", reason="Install the notebooks extra for execution tests.")
    root = Path(__file__).resolve().parents[1]
    notebook = nbformat.read(root / "notebooks/governance" / name, as_version=4)
    nbformat.validate(notebook)
    assert all(not cell.get("outputs") and cell.get("execution_count") is None
               for cell in notebook.cells if cell.cell_type == "code")
    guard = nbformat.v4.new_code_cell(
        "import subprocess, httpx\n"
        "from azure.identity import DefaultAzureCredential\n"
        "def forbidden(*args, **kwargs):\n"
        "    raise AssertionError('Offline notebook attempted a service or subprocess call')\n"
        "subprocess.run = forbidden\n"
        "httpx.Client.send = forbidden\n"
        "DefaultAzureCredential.get_token = forbidden\n"
    )
    notebook.cells.insert(0, guard)
    working_directory = root / "notebooks/governance" if name.startswith(("02", "04")) else root
    executed = nbclient.NotebookClient(
        notebook, timeout=90, kernel_name="python3",
        resources={"metadata": {"path": str(working_directory)}},
    ).execute()
    assert not any(
        output.output_type == "error"
        for cell in executed.cells if cell.cell_type == "code" for output in cell.outputs
    )
