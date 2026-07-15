"""
GenAI tracing for Foundry agents (P1.4 — cross-framework observability).

Wires OpenTelemetry GenAI spans for every agent / model / tool call via
``AIProjectInstrumentor``. This is Microsoft's framework-agnostic tracing story
(June 2026): the same instrumentation works whether the agent runs on Foundry
Agent Service, Agent Framework, or a hosted container.

Export targets, in order of preference:
    1. **Azure Monitor / Foundry Observability** — when an Application Insights
       connection string is available (``APPLICATIONINSIGHTS_CONNECTION_STRING``
       or passed explicitly). Spans then appear in the Foundry portal's
       Observability tab.
    2. **Console** — fallback for local development.

Content recording (prompts, completions, tool arguments) is **disabled by
default** because HR policy conversations may contain personal data. Opt in
explicitly with ``enable_content_recording=True`` only in environments where
that is acceptable.

Usage:
    from src.observability import enable_tracing

    enable_tracing()  # call once at process startup

Reference:
    https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-client-side?tabs=python
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Experimental preview flag required by azure-ai-projects to emit GenAI spans.
_GENAI_TRACING_ENV = "AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"
# Controls whether prompt/response content is captured on spans.
_CONTENT_RECORDING_ENV = "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"

_ENABLED = False


def is_tracing_enabled() -> bool:
    """Return True if GenAI tracing has been wired up in this process."""
    return _ENABLED


def enable_tracing(
    connection_string: Optional[str] = None,
    *,
    enable_content_recording: bool = False,
) -> bool:
    """Enable GenAI tracing for Foundry agent/model/tool calls.

    Idempotent: safe to call more than once; subsequent calls are no-ops.

    Args:
        connection_string: Application Insights connection string. Falls back to
            ``APPLICATIONINSIGHTS_CONNECTION_STRING``. When absent, spans are
            exported to the console.
        enable_content_recording: Capture prompt/response content on spans.
            Defaults to ``False`` to avoid recording potentially sensitive HR
            data.

    Returns:
        ``True`` if instrumentation was enabled, ``False`` if the required
        packages were unavailable (tracing is best-effort and never fatal).
    """
    global _ENABLED
    if _ENABLED:
        return True

    try:
        from azure.core.settings import settings
        from azure.ai.projects.telemetry import AIProjectInstrumentor
    except ImportError as exc:  # pragma: no cover - depends on optional install
        logger.warning(
            "GenAI tracing unavailable (azure-ai-projects telemetry not "
            "importable): %s",
            exc,
        )
        return False

    settings.tracing_implementation = "opentelemetry"

    # Opt in to the experimental GenAI spans unless the caller overrode it.
    os.environ.setdefault(_GENAI_TRACING_ENV, "true")
    os.environ[_CONTENT_RECORDING_ENV] = "true" if enable_content_recording else "false"

    conn = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    exporter = "console"

    if conn:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=conn)
            exporter = "azure-monitor"
        except ImportError:  # pragma: no cover - optional dependency
            logger.warning(
                "azure-monitor-opentelemetry not installed; falling back to "
                "console span export."
            )
            _configure_console_exporter()
    else:
        _configure_console_exporter()

    AIProjectInstrumentor().instrument()
    _ENABLED = True
    logger.info(
        "GenAI tracing enabled (exporter=%s, content_recording=%s)",
        exporter,
        enable_content_recording,
    )
    return True


def _configure_console_exporter() -> None:
    """Attach a console span exporter without clobbering an existing provider."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))


def disable_tracing() -> None:
    """Remove GenAI instrumentation (primarily for tests)."""
    global _ENABLED
    try:
        from azure.ai.projects.telemetry import AIProjectInstrumentor

        instrumentor = AIProjectInstrumentor()
        if instrumentor.is_instrumented():
            instrumentor.uninstrument()
    except Exception:  # pragma: no cover - best effort
        pass
    _ENABLED = False
