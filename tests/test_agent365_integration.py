from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scripts.demo import agent365_preflight as preflight


@pytest.mark.parametrize("connection_string", [None, "InstrumentationKey=synthetic"])
def test_hosted_server_uses_only_host_managed_observability(monkeypatch, connection_string):
    import agent_framework
    import agent_framework.foundry
    import agent_framework_foundry_hosting
    import azure.identity
    import src.observability

    host = MagicMock()
    legacy_tracing = MagicMock()
    monkeypatch.setattr(agent_framework, "Agent", MagicMock())
    monkeypatch.setattr(agent_framework, "tool", lambda **kwargs: lambda fn: fn)
    monkeypatch.setattr(agent_framework.foundry, "FoundryChatClient", MagicMock())
    monkeypatch.setattr(agent_framework_foundry_hosting, "ResponsesHostServer", host)
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", MagicMock())
    monkeypatch.setattr(src.observability, "enable_tracing", legacy_tracing)
    monkeypatch.setitem(
        sys.modules, "retrieval",
        SimpleNamespace(normalize_retrieval_mode=lambda value: "tool"),
    )
    if connection_string:
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", connection_string)
    else:
        monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    path = Path(__file__).resolve().parents[1] / "src/hosted_agent/server.py"

    module = runpy.run_path(str(path))

    host.assert_called_once_with(
        module["agent"], applicationinsights_connection_string=connection_string
    )
    legacy_tracing.assert_not_called()


def test_hosted_search_logs_no_conversation_content(monkeypatch, caplog):
    import agent_framework
    import agent_framework.foundry
    import agent_framework_foundry_hosting
    import azure.identity
    import azure.search.documents

    monkeypatch.setattr(agent_framework, "Agent", MagicMock())
    monkeypatch.setattr(agent_framework, "tool", lambda **kwargs: lambda fn: fn)
    monkeypatch.setattr(agent_framework.foundry, "FoundryChatClient", MagicMock())
    monkeypatch.setattr(agent_framework_foundry_hosting, "ResponsesHostServer", MagicMock())
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", MagicMock())
    search = MagicMock()
    search.return_value.search.return_value = []
    monkeypatch.setattr(azure.search.documents, "SearchClient", search)
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://synthetic.search.windows.net")
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "true")
    monkeypatch.setitem(
        sys.modules, "retrieval",
        SimpleNamespace(normalize_retrieval_mode=lambda value: "tool"),
    )
    path = Path(__file__).resolve().parents[1] / "src/hosted_agent/server.py"
    module = runpy.run_path(str(path))
    caplog.set_level("INFO")

    module["search_hr_policies"]("my private pto question")

    assert "glossary_expanded=True" in caplog.text
    assert "private" not in caplog.text
    assert "Paid Time Off" not in caplog.text


@pytest.mark.parametrize("enabled", [True, False])
def test_native_host_export_respects_platform_agent365_flag(monkeypatch, enabled):
    from azure.ai.agentserver.core import configure_observability
    import microsoft.opentelemetry

    configure = MagicMock()
    monkeypatch.setattr(microsoft.opentelemetry, "use_microsoft_opentelemetry", configure)
    monkeypatch.setenv("FOUNDRY_HOSTING_ENVIRONMENT", "test")
    monkeypatch.setenv("FOUNDRY_AGENT365_TRACING_ENABLED", str(enabled).lower())
    monkeypatch.setenv("FOUNDRY_AGENT_INSTANCE_CLIENT_ID", "synthetic-agent-id")

    configure_observability(connection_string="InstrumentationKey=synthetic")

    options = configure.call_args.kwargs
    assert options["enable_azure_monitor"] is True
    assert options["enable_sensitive_data"] is False
    if enabled:
        assert options["enable_a365"] is True
        assert options["a365_use_s2s_endpoint"] is True
        assert options["a365_observability_scope_override"] == (
            "api://9b975845-388f-4429-889e-eab1ef63949c/.default"
        )
    else:
        assert "enable_a365" not in options


@pytest.fixture
def fake_azure(monkeypatch):
    responses = [
        {"properties": {"a365LoggingEnabled": True, "a365Status": "Enabled"}},
        {"value": [{"id": "observability", "appRoles": [
            {"id": preflight.OTEL_WRITE_ROLE, "isEnabled": True},
        ]}]},
        {"displayName": "hosted-agent", "appId": "agent-app"},
        {"value": [{"resourceId": "observability", "appRoleId": preflight.OTEL_WRITE_ROLE}]},
        {"pricingTier": "Standard", "extensions": [
            {"name": "AIPromptEvidence", "isEnabled": "True"},
        ]},
    ]
    commands = []

    def az_json(*args):
        commands.append(args)
        return responses[len(commands) - 1]

    monkeypatch.setattr(preflight, "az_json", az_json)
    return responses, commands


def test_preflight_checks_configuration_without_claiming_ingestion(fake_azure):
    _, commands = fake_azure
    checks = preflight.collect_checks("/account", ["agent-object"])
    assert all(row.status == "PASS" for row in checks[:-1])
    assert checks[-1].status == "UNKNOWN"
    assert all("POST" not in command and "update" not in command for command in commands)


@pytest.mark.parametrize("property_name,value", [
    ("a365Status", "NotLicensed"), ("a365LoggingEnabled", False),
])
def test_preflight_rejects_disabled_or_unlicensed_collection(fake_azure, property_name, value):
    responses, _ = fake_azure
    responses[0]["properties"][property_name] = value
    assert preflight.collect_checks("/account", ["agent-object"])[0].status == "FAIL"


@pytest.mark.parametrize("assignments", [
    [],
    [{"resourceId": "wrong-service", "appRoleId": preflight.OTEL_WRITE_ROLE}],
    [{"resourceId": "observability", "appRoleId": "wrong-role"}],
])
def test_preflight_requires_exact_role_and_resource(fake_azure, assignments):
    responses, _ = fake_azure
    responses[3]["value"] = assignments
    checks = preflight.collect_checks("/account", ["agent-object"])
    assert checks[2].status == "FAIL"


def test_preflight_does_not_accept_ambiguous_observability_service(fake_azure):
    responses, _ = fake_azure
    responses[1]["value"] *= 2
    checks = preflight.collect_checks("/account", ["agent-object"])
    assert checks[-1].status == "FAIL"


def test_az_failure_surfaces_stderr(monkeypatch):
    monkeypatch.setattr(
        preflight.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="Authorization denied"
        ),
    )
    with pytest.raises(RuntimeError, match="Authorization denied"):
        preflight.az_json("account", "show")
