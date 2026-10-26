"""Offline inspection of native hosting telemetry; no exporters or credentials run."""

from __future__ import annotations

import ast
import logging
import os
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch


def integration_packages() -> list[dict[str, str]]:
    return [
        {"package": package, "installed_version": version(package), "role": role}
        for package, role in (
            ("agent-framework-foundry-hosting", "ResponsesHostServer entry point"),
            ("azure-ai-agentserver-core", "Native observability configuration"),
            ("microsoft-opentelemetry", "Unified telemetry distribution"),
        )
    ]


def hosted_entrypoint_source() -> str:
    """Read the actual host assignment without importing or starting the agent."""
    path = Path(__file__).resolve().parents[2] / "src/hosted_agent/server.py"
    source = path.read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "server" for target in node.targets)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "ResponsesHostServer"
        ):
            excerpt = ast.get_source_segment(source, node)
            if excerpt:
                return excerpt
    raise RuntimeError("The hosted entry point changed; update the walkthrough before presenting it.")


def inspect_native_wiring(*, agent365_enabled: bool) -> dict[str, str | bool]:
    """Exercise installed host configuration, intercepting the distro initializer.

    Only hosted feature flags are simulated. No agent identities are supplied,
    no provider is installed, and raw configuration arguments are not returned.
    """
    from azure.ai.agentserver.core import configure_observability
    import microsoft.opentelemetry

    root = logging.getLogger()
    with (
        patch.dict(os.environ, {
            "FOUNDRY_HOSTING_ENVIRONMENT": "offline-wiring-example",
            "FOUNDRY_AGENT365_TRACING_ENABLED": str(agent365_enabled).lower(),
        }),
        patch.object(microsoft.opentelemetry, "use_microsoft_opentelemetry") as configure,
        patch.object(root, "setLevel"),
        patch.object(root, "addHandler"),
        patch("azure.ai.agentserver.core._tracing.logger"),
    ):
        # DEBUG skips the host's mutation of other loggers' levels.
        configure_observability(
            connection_string="offline-placeholder-not-a-credential", log_level="DEBUG",
        )
        configure.assert_called_once()
        options = configure.call_args.kwargs
        return {
            "mode": "Offline SDK wiring only; distro initializer mocked",
            "simulated_platform_flag": agent365_enabled,
            "azure_monitor_requested": options.get("enable_azure_monitor") is True,
            "agent365_requested": options.get("enable_a365") is True,
            "agent365_s2s_requested": options.get("a365_use_s2s_endpoint") is True,
            "sensitive_content_enabled": options.get("enable_sensitive_data") is True,
            "exporter_executed": False,
            "ingestion": "Not tested",
        }
