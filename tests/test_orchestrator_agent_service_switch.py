"""Tests for the orchestrator's ``AGENT_SERVICE`` switch.

Verifies that ``HRPolicyWorkflowOrchestrator`` instantiates the correct
``HRPolicyAgent`` implementation depending on ``AGENT_SERVICE``:

- ``foundry`` \u2192 ``src.agents.hr_policy_agent.HRPolicyAgent``
  (Pattern B \u2014 PromptAgent + MCPTool)
- anything else (default ``agent-framework``) \u2192
  ``src.agents.hr_policy_agent_af.HRPolicyAgent``
  (Hosted Agent \u2014 Microsoft Agent Framework + ``@tool``)

These tests do not exercise any Azure SDK calls \u2014 they only check the
class selection inside ``_build_hr_agent``.
"""

import os
import pytest

from src.agents.orchestrator import HRPolicyWorkflowOrchestrator


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Ensure no stray env vars leak in from the host shell."""
    monkeypatch.delenv("AGENT_SERVICE", raising=False)
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://example.foundry.azure.com")
    yield


def test_agent_service_foundry_selects_pattern_b(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE", "foundry")

    orch = HRPolicyWorkflowOrchestrator(use_azure=False)
    agent = orch._build_hr_agent()

    from src.agents.hr_policy_agent import HRPolicyAgent as FoundryHRPolicyAgent
    assert isinstance(agent, FoundryHRPolicyAgent)
    assert orch.agent_service == "foundry"


def test_agent_service_default_selects_agent_framework():
    """No ``AGENT_SERVICE`` env var \u2192 default ``agent-framework`` (Hosted Agent)."""
    orch = HRPolicyWorkflowOrchestrator(use_azure=False)
    agent = orch._build_hr_agent()

    from src.agents.hr_policy_agent_af import HRPolicyAgent as AFHRPolicyAgent
    assert isinstance(agent, AFHRPolicyAgent)
    assert orch.agent_service == "agent-framework"


def test_agent_service_explicit_agent_framework(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE", "agent-framework")

    orch = HRPolicyWorkflowOrchestrator(use_azure=False)
    agent = orch._build_hr_agent()

    from src.agents.hr_policy_agent_af import HRPolicyAgent as AFHRPolicyAgent
    assert isinstance(agent, AFHRPolicyAgent)


def test_agent_service_alias_underscore(monkeypatch):
    """Hyphen / underscore variants normalize to the same selection."""
    monkeypatch.setenv("AGENT_SERVICE", "foundry_agent_service")

    orch = HRPolicyWorkflowOrchestrator(use_azure=False)
    assert orch.agent_service == "foundry"


def test_agent_service_unknown_falls_back_to_agent_framework(monkeypatch, caplog):
    monkeypatch.setenv("AGENT_SERVICE", "rogue-implementation")

    with caplog.at_level("WARNING"):
        orch = HRPolicyWorkflowOrchestrator(use_azure=False)

    assert orch.agent_service == "agent-framework"
    assert any("Unknown AGENT_SERVICE" in rec.message for rec in caplog.records)


def test_constructor_argument_overrides_env(monkeypatch):
    """``agent_service=`` constructor arg wins over the env var."""
    monkeypatch.setenv("AGENT_SERVICE", "agent-framework")

    orch = HRPolicyWorkflowOrchestrator(use_azure=False, agent_service="foundry")
    assert orch.agent_service == "foundry"
