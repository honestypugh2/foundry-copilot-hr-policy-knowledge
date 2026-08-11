import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Overview, Pareto } from "./BenchmarkWorkbench";

const experiment = {
  schema_version: "1.0",
  experiment_id: "synthetic-pattern-a",
  pattern: "A",
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
  blockers: ["No compatible configuration passes all SLO and publication gates."],
};

function mockBenchmarkApi(items = [experiment]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    return new Response(JSON.stringify(
      url.includes("/decisions")
        ? { ...decision, evidence: items.length ? decision.evidence : [], selected_scope: items.length ? decision.selected_scope : null }
        : { schema_version: "1.0", items }
    ));
  });
}

afterEach(() => vi.restoreAllMocks());

describe("benchmark workbench", () => {
  it("renders measured values without turning unavailable cost into zero", async () => {
    mockBenchmarkApi();
    render(<Overview />);

    expect(await screen.findByText("158 ms")).toBeInTheDocument();
    expect(screen.getByText("84.0%")).toBeInTheDocument();
    expect(screen.getByText("No publishable recommendation")).toBeInTheDocument();
    expect(screen.queryByText("$0")).not.toBeInTheDocument();
  });

  it("shows an explicit empty artifact state", async () => {
    mockBenchmarkApi([]);
    render(<Overview />);

    expect(await screen.findByText("No experiment artifacts are configured.")).toBeInTheDocument();
  });

  it("renders an accessible nonblank Pareto point", async () => {
    mockBenchmarkApi();
    const { container } = render(<Pareto />);

    await waitFor(() => expect(container.querySelector(".plot-point")).toBeInTheDocument());
    expect(screen.getByLabelText("Quality and latency plot")).toBeInTheDocument();
  });
});