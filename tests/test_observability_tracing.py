from unittest.mock import MagicMock

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

import src.observability.tracing as tracing


def test_disabling_ai_client_wrapper_keeps_span_export_enabled(monkeypatch):
    from azure.ai.projects import telemetry

    instrument = MagicMock()
    configure_console_exporter = MagicMock()
    monkeypatch.setattr(tracing, "_ENABLED", False)
    monkeypatch.setattr(telemetry.AIProjectInstrumentor, "instrument", instrument)
    monkeypatch.setattr(tracing, "_configure_console_exporter", configure_console_exporter)
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)

    enabled = tracing.enable_tracing(instrument_ai_clients=False)

    assert enabled is True
    assert tracing.is_tracing_enabled() is True
    assert tracing.os.environ[tracing._GENAI_TRACING_ENV] == "false"
    instrument.assert_not_called()
    configure_console_exporter.assert_called_once_with()


def test_flush_tracing_flushes_sdk_provider(monkeypatch):
    provider = TracerProvider()
    force_flush = MagicMock(return_value=True)
    monkeypatch.setattr(provider, "force_flush", force_flush)
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: provider)

    assert tracing.flush_tracing(timeout_millis=1234) is True
    force_flush.assert_called_once_with(timeout_millis=1234)