import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Coverage, Overview, Pareto } from "./BenchmarkWorkbench";

const experiment = {
  schema_version: "1.0",
  experiment_id: "synthetic-pattern-a",
  pattern: "A",
  retrieval_mode: "classic-hybrid",
  dataset_name: "synthetic-hr-gold",
  dataset_version: "1.0",
  git_commit: "synthetic",
  corpus_fingerprint: "corpus-hash",
  index_fingerprint: "index-hash",
  model_deployment: null,
  created_at: "2026-08-03T12:00:00Z",
  count: 30,
  success_rate: 0.97,
  latency_p50_ms: 105,
  latency_p95_ms: 158,
  latency_p99_ms: 176,
  quality: 0.84,
  security_pass_rate: 1,
  estimated_variable_cost: null,
  sample_warning: null,
  comparison_scope: "scope-hash",
  provenance: { synthetic: true },
};

const decision = {
  schema_version: "1.0",
  goal: "balanced",
  thresholds: {
    minimum_quality: 0.8,
    maximum_latency_p95_ms: 1000,
    minimum_success_rate: 0.95,
    minimum_security_pass_rate: 1,
    maximum_estimated_variable_cost: 0.05,
  },
  selected_scope: "scope-hash",
  available_scopes: [{ scope_id: "scope-hash", experiment_ids: [experiment.experiment_id] }],
  evidence: [{
    experiment_id: experiment.experiment_id,
    pattern: "A",
    qualified: false,
    qualification_failures: ["estimated_variable_cost: unavailable"],
    on_pareto_frontier: false,
    publication_ready: false,
    publication_blockers: ["synthetic evidence"],
  }],
  frontier_experiment_ids: [],
  recommended_experiment_id: null,
  selection_method: "minimum equal-weight normalized distance",
  blockers: ["No compatible configuration passes all SLO and release-readiness gates."],
};

const capabilities = [{
  capability_id: "grafana-dashboards",
  name: "Application Insights dashboards with Grafana",
  classification: "reuse",
  status: "not_configured",
  implementation_status: "partial",
  release_status: "GA",
  source_version: "azure-monitor",
  authoritative_system: "Azure Managed Grafana",
  component: "infra/bicep/main.bicep",
  configuration_source: "BENCHMARK_LINK_GRAFANA",
  limitations: ["Versioned dashboards and alert rules are not yet committed."],
  deep_link_type: "grafana",
  artifact_count: 0,
}];

function mockBenchmarkApi(items = [experiment]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const pattern = url.match(/\/patterns\/([^/]+)\/summary/)?.[1];
    return new Response(JSON.stringify(
      url.includes("/links/")
        ? { schema_version: "1.0", resource_type: url.includes("application_insights") ? "application_insights" : "test", source_id: "current", status: "not_configured", authoritative_url: null, release_status: url.includes("application_insights") ? "Preview" : "GA" }
      : url.includes("/decisions")
        ? { ...decision, evidence: items.length ? decision.evidence : [], selected_scope: items.length ? decision.selected_scope : null }
        : url.includes("/capabilities")
          ? { schema_version: "1.0", source_version: "test", capabilities }
        : pattern
          ? { schema_version: "1.0", item: { pattern, automation_boundary: `automated ${pattern}`, telemetry_boundary: "test telemetry", implementation_status: "implemented", evidence_status: pattern === "A" && items.length ? "fixture_only" : "run_required", experiment_count: pattern === "A" ? items.length : 0, latest: pattern === "A" ? items[0] ?? null : null } }
        : { schema_version: "1.0", items }
    ));
  });
}

afterEach(() => vi.restoreAllMocks());

describe("benchmark workbench", () => {
  it("renders measured values without turning unavailable cost into zero", async () => {
    mockBenchmarkApi();
    render(<Overview />);

    expect(await screen.findByRole("heading", { name: "Grounded agent — architecture benchmark" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Azure tools explain each system. This benchmark helps you choose across them." })).toBeInTheDocument();
    expect(screen.getByText("Cross-pattern comparison")).toBeInTheDocument();
    expect(screen.getAllByText("Copilot Studio", { exact: true }).length).toBeGreaterThan(0);
    expect(screen.getByText("Production · Azure services lead")).toBeInTheDocument();
    expect(await screen.findByText("158 ms")).toBeInTheDocument();
    expect(screen.getByText("84.0%")).toBeInTheDocument();
    expect(screen.getByText("No comparable evidence to recommend yet")).toBeInTheDocument();
    expect(screen.queryByText("$0")).not.toBeInTheDocument();
  });

  it("shows an explicit empty artifact state", async () => {
    mockBenchmarkApi([]);
    render(<Overview />);

    expect(await screen.findByText("No experiment artifacts are configured.")).toBeInTheDocument();
  });

  it("renders the Pareto view with comparable evidence", async () => {
    mockBenchmarkApi();
    render(<Pareto />);

    expect(await screen.findByRole("heading", { name: "Pareto and SLO" })).toBeInTheDocument();
    expect(await screen.findByText("Pareto frontier")).toBeInTheDocument();
    expect(screen.getAllByText("synthetic-pattern-a").length).toBeGreaterThan(0);
  });

  it("renders source-specific evidence investigation guidance", async () => {
    mockBenchmarkApi();
    render(<Coverage />);

    expect(await screen.findByText("Request duration and failure trends in Performance")).toBeInTheDocument();
    expect(screen.getByText("Agent details: Preview")).toBeInTheDocument();
    expect(screen.getByText("Agent Monitoring: Preview")).toBeInTheDocument();
    expect(screen.getByText("Open Performance, select the operation", { exact: false })).toBeInTheDocument();
    expect(screen.getAllByText("How to investigate")).toHaveLength(5);
    expect(screen.getByText("BENCHMARK_LINK_APPLICATION_INSIGHTS")).toBeInTheDocument();
    expect(screen.queryByText("Benchmark Blog Outline readiness")).not.toBeInTheDocument();
    expect(screen.queryByText("All repository and Microsoft capabilities")).not.toBeInTheDocument();
  });
});