"""
GenAI tracing for Foundry agents (P1.4 — cross-framework observability).

Configures OpenTelemetry export and benchmark correlation. Microsoft Agent
Framework emits its own agent, model, workflow, and tool spans. The legacy
``AIProjectInstrumentor`` path remains available for compatible clients, but is
disabled by Agent Framework hosts because its OpenAI stream wrapper is
incompatible with ``FoundryChatClient`` streaming.

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
    instrument_ai_clients: bool = True,
    sampling_ratio: float | None = None,
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
        instrument_ai_clients: Apply ``AIProjectInstrumentor`` to model clients.
            Disable when a client is incompatible with the OpenAI stream wrapper;
            OpenTelemetry application spans and export remain enabled.
        sampling_ratio: Optional Azure Monitor trace sampling ratio from 0.0 to
            1.0. Controlled benchmarks use 1.0 so every measured invocation is
            eligible for connected trace validation.

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

    # The experimental flag wraps OpenAI streams and is only needed for the
    # AI-client instrumentation path, not custom application spans.
    os.environ[_GENAI_TRACING_ENV] = "true" if instrument_ai_clients else "false"
    os.environ[_CONTENT_RECORDING_ENV] = "true" if enable_content_recording else "false"

    conn = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    exporter = "console"

    if conn:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            instrumentation_options = None
            if not instrument_ai_clients:
                instrumentation_options = {"openai": {"enabled": False}}
            azure_monitor_options = {
                "connection_string": conn,
                "instrumentation_options": instrumentation_options,
            }
            if sampling_ratio is not None:
                if not 0.0 <= sampling_ratio <= 1.0:
                    raise ValueError("sampling_ratio must be between 0.0 and 1.0")
                azure_monitor_options["sampling_ratio"] = sampling_ratio
            configure_azure_monitor(
                **azure_monitor_options,
            )
            exporter = "azure-monitor"
        except ImportError:  # pragma: no cover - optional dependency
            logger.warning(
                "azure-monitor-opentelemetry not installed; falling back to "
                "console span export."
            )
            _configure_console_exporter()
    else:
        _configure_console_exporter()

    if instrument_ai_clients:
        AIProjectInstrumentor().instrument()
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    from src.observability.benchmark_correlation import (
        BenchmarkCorrelationSpanProcessor,
    )

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.add_span_processor(BenchmarkCorrelationSpanProcessor())
    _ENABLED = True
    logger.info(
        "GenAI tracing enabled (exporter=%s, content_recording=%s, "
        "ai_client_instrumentation=%s)",
        exporter,
        enable_content_recording,
        instrument_ai_clients,
    )
    return True


def flush_tracing(timeout_millis: int = 30_000) -> bool:
    """Flush pending spans before a short-lived process exits."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        return False
    return provider.force_flush(timeout_millis=timeout_millis)


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
