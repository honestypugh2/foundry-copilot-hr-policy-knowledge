"""Executable Microsoft Asset Reuse Matrix for benchmark capabilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.benchmarking.api.models import Capability, CapabilityState

_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    name: str
    classification: Literal["reuse", "adapter", "new_gap_coverage"]
    implementation_status: Literal["implemented", "partial", "external_reference"]
    release_status: str
    source_version: str
    authoritative_system: str
    component: str | None
    configuration_source: str | None = None
    limitations: tuple[str, ...] = ()
    deep_link_type: str | None = None


CAPABILITY_REGISTRY: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("app-insights-agent-details", "Application Insights Agent details", "reuse", "partial", "Preview", "genai-otel", "Application Insights", "src/observability/tracing.py", "BENCHMARK_LINK_APPLICATION_INSIGHTS", ("Prompt and response content recording is disabled by default.", "Connected validation must confirm response-model and session attributes after deployment."), "application_insights"),
    CapabilitySpec("grafana-dashboards", "Application Insights dashboards with Grafana", "reuse", "partial", "GA", "azure-monitor", "Azure Managed Grafana", "infra/bicep/main.bicep", "BENCHMARK_LINK_GRAFANA", ("The Grafana resource exists, but versioned dashboards and alert rules are not yet committed."), "grafana"),
    CapabilitySpec("foundry-monitoring-evaluation", "Foundry Agent Monitoring and evaluation reports", "reuse", "partial", "provider-dependent", "foundry-evaluation", "Microsoft Foundry", "src/evaluation/run_eval.py", "BENCHMARK_LINK_FOUNDRY", ("Cloud evaluation results require normalization before cross-pattern comparison.",), "foundry"),
    CapabilitySpec("search-demo-locust", "Azure Search OpenAI Demo and Locust", "reuse", "implemented", "GA", "locust", "Azure Load Testing", "locustfile.py", "BENCHMARK_LINK_LOAD_TESTING", ("Load-test evidence remains separate from controlled experiment evidence.",), "load_testing"),
    CapabilitySpec("search-classic-response", "Azure AI Search classic query response", "adapter", "implemented", "GA", "search-sdk", "Azure AI Search", "src/benchmarking/adapters/direct_search.py", None, ("Service elapsed time is unavailable when the active SDK boundary omits it.",), "search"),
    CapabilitySpec("search-knowledge-base-retrieve", "Azure AI Search Knowledge Base retrieve", "adapter", "implemented", "GA/Preview", "2026-04-01", "Azure AI Search", "src/benchmarking/adapters/knowledge_base.py", None, ("Preview API use must be explicitly selected and recorded.",), "search"),
    CapabilitySpec("foundry-agent-mcp", "Foundry Agent Service plus MCP", "adapter", "implemented", "provider-dependent", "foundry-agent-service", "Microsoft Foundry", "src/benchmarking/adapters/agent.py", None, ("MCP-internal timing is unavailable unless emitted by the provider.",), "foundry"),
    CapabilitySpec("pattern-c-hosted-call-sites", "Pattern C and Hosted Agent call sites", "adapter", "implemented", "GA", "artifact-schema-1.0", "Repository runtime", "src/benchmarking/adapters/pattern_c.py", None, ("Hosted cold-start and deterministic locator semantics are reported separately.",)),
    CapabilitySpec("copilot-studio-patterns", "Copilot Studio A/A2/B/C/Hosted", "adapter", "implemented", "provider-dependent", "direct-line", "Microsoft Copilot Studio", "src/benchmarking/adapters/copilot_studio.py", "COPILOT_STUDIO_TOKEN_ENDPOINT", ("Copilot-owned generation is outside repository instrumentation.",)),
    CapabilitySpec("rag-experiment-accelerator", "RAG Experiment Accelerator", "reuse", "external_reference", "provider-dependent", "external", "Microsoft Foundry", None, None, ("No stable repository adapter is currently configured.",)),
    CapabilitySpec("foundry-rag-evaluators", "Foundry RAG evaluators", "adapter", "partial", "provider-dependent", "azure-ai-evaluation", "Microsoft Foundry", "src/evaluation/run_eval.py", "BENCHMARK_LINK_FOUNDRY", ("Judge scores require calibration against deterministic checks and a reviewed gold set.",), "foundry"),
    CapabilitySpec("foundry-otel-tracing", "Foundry/OpenTelemetry tracing", "adapter", "implemented", "GA", "genai-otel", "Application Insights", "src/observability/benchmark_correlation.py", "APPLICATIONINSIGHTS_CONNECTION_STRING", ("Only low-cardinality benchmark baggage is copied to spans.",), "application_insights"),
    CapabilitySpec("monitor-search-kql", "Azure Monitor and Search diagnostic KQL", "reuse", "implemented", "GA", "kql-v1", "Azure Monitor", "experiments/kql", "BENCHMARK_LINK_APPLICATION_INSIGHTS", ("Queries must remain time-bounded and resource-scoped.",), "application_insights"),
    CapabilitySpec("azure-cost-management", "Azure Cost Management", "reuse", "partial", "GA", "cost-management", "Azure Cost Management", "src/benchmarking/costing.py", "BENCHMARK_LINK_COST_MANAGEMENT", ("Per-request estimates require a versioned profile and service-reported quantities.", "A dated billed-cost reconciliation export is not yet committed."), "cost_management"),
    CapabilitySpec("normalized-decision-contracts", "Normalized contracts, comparison, regressions, Pareto, and SLO qualification", "new_gap_coverage", "implemented", "Repository", "artifact-schema-1.0", "Benchmark API", "src/benchmarking/decision.py", None, ("Recommendations fail closed when required evidence is missing or incompatible.",)),
    CapabilitySpec("benchmark-decision-workbench", "Read-only benchmark decision workbench", "new_gap_coverage", "implemented", "Repository", "benchmark-api-1.0", "Benchmark Workbench", "src/frontend/src/pages/BenchmarkWorkbench.tsx", None, ("Native trace, evaluation, dashboard, and billing experiences remain authoritative.",)),
)


def capability_inventory(artifact_count: int) -> list[Capability]:
    return [
        Capability(
            capability_id=spec.capability_id,
            name=spec.name,
            classification=spec.classification,
            status=_status(spec),
            implementation_status=spec.implementation_status,
            freshness=_freshness(spec),
            release_status=spec.release_status,
            source_version=spec.source_version,
            authoritative_system=spec.authoritative_system,
            component=spec.component,
            configuration_source=spec.configuration_source,
            limitations=list(spec.limitations),
            deep_link_type=spec.deep_link_type,
            artifact_count=(artifact_count if spec.capability_id == "normalized-decision-contracts" else 0),
        )
        for spec in CAPABILITY_REGISTRY
    ]


def _status(spec: CapabilitySpec) -> CapabilityState:
    if spec.implementation_status == "external_reference":
        return "not_applicable"
    if spec.configuration_source and not os.getenv(spec.configuration_source):
        return "not_configured"
    if spec.component and not (_ROOT / spec.component).exists():
        return "unavailable"
    return "available"


def _freshness(spec: CapabilitySpec) -> str:
    if spec.configuration_source:
        return "configured" if os.getenv(spec.configuration_source) else "configuration required"
    if spec.implementation_status == "external_reference":
        return "external reference only"
    return "repository-backed"