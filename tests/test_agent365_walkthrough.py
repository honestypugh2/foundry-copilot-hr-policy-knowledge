from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from opentelemetry import trace

from src.governance import agent365_walkthrough as walkthrough


def test_reference_reads_host_source_without_importing_agent():
    source = walkthrough.hosted_entrypoint_source()
    assert source.startswith("server = ResponsesHostServer(")
    assert "APPLICATIONINSIGHTS_CONNECTION_STRING" in source
    assert "server.run()" not in source
    assert "enable_tracing" not in source


def test_packages_report_installed_versions_and_missing_packages_fail(monkeypatch):
    rows = walkthrough.integration_packages()
    assert {row["package"] for row in rows} == {
        "agent-framework-foundry-hosting", "azure-ai-agentserver-core", "microsoft-opentelemetry",
    }
    assert all(row["installed_version"] for row in rows)
    monkeypatch.setattr(walkthrough, "version", MagicMock(side_effect=RuntimeError("missing package")))
    with pytest.raises(RuntimeError, match="missing package"):
        walkthrough.integration_packages()


@pytest.mark.parametrize("enabled", [False, True])
def test_mocked_sdk_wiring_is_offline_private_and_restores_state(monkeypatch, enabled):
    import httpx
    import microsoft.opentelemetry
    from azure.identity import DefaultAzureCredential

    forbidden = MagicMock(side_effect=AssertionError("No service calls allowed"))
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(DefaultAzureCredential, "get_token", forbidden)
    monkeypatch.setenv("FOUNDRY_HOSTING_ENVIRONMENT", "original-context")
    monkeypatch.setenv("FOUNDRY_AGENT_INSTANCE_CLIENT_ID", "private-identity-not-for-display")
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "private-connection-not-for-display")
    env_before = dict(os.environ)
    root = logging.getLogger()
    level_before, handlers_before = root.level, tuple(root.handlers)
    provider_before = trace.get_tracer_provider()
    initializer_before = microsoft.opentelemetry.use_microsoft_opentelemetry

    result = walkthrough.inspect_native_wiring(agent365_enabled=enabled)

    assert result["agent365_requested"] is enabled
    assert result["agent365_s2s_requested"] is enabled
    assert result["azure_monitor_requested"] is True
    assert result["sensitive_content_enabled"] is False
    assert result["exporter_executed"] is False
    assert result["ingestion"] == "Not tested"
    assert "private-" not in str(result)
    assert dict(os.environ) == env_before
    assert trace.get_tracer_provider() is provider_before
    assert microsoft.opentelemetry.use_microsoft_opentelemetry is initializer_before
    assert root.level == level_before and tuple(root.handlers) == handlers_before
    forbidden.assert_not_called()


def test_wiring_drift_fails_explicitly_without_installing_a_provider(monkeypatch):
    import azure.ai.agentserver.core

    monkeypatch.setattr(azure.ai.agentserver.core, "configure_observability", lambda **kwargs: None)
    env_before = dict(os.environ)
    with pytest.raises(AssertionError, match="called once"):
        walkthrough.inspect_native_wiring(agent365_enabled=True)
    assert dict(os.environ) == env_before


def test_notebook_contains_explicit_sdk_evidence_boundaries():
    nbformat = pytest.importorskip("nbformat")
    path = Path(__file__).resolve().parents[1] / "notebooks/governance/03_follow_the_evidence.ipynb"
    notebook = nbformat.read(path, as_version=4)
    cells = {cell.id: cell.source for cell in notebook.cells}
    assert "inspect_native_wiring" in cells["signals-sdk-offline-example"]
    assert "Configuration evidence is not delivery evidence" in cells["signals-sdk-privacy-prerequisites"]
    assert "no fabricated agent identity" in cells["signals-sdk-offline-contract"]
    assert "not the entire Agent 365 SDK" in cells["signals-sdk-ownership"]
