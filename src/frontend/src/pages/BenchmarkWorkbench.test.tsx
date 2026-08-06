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
  provenance: { synthetic: true },
};

afterEach(() => vi.restoreAllMocks());

describe("benchmark workbench", () => {
  it("renders measured values without turning unavailable cost into zero", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ schema_version: "1.0", items: [experiment] }))
    );
    render(<Overview />);

    expect(await screen.findAllByText("158 ms")).toHaveLength(2);
    expect(screen.getAllByText("84.0%")).toHaveLength(2);
    expect(screen.queryByText("$0")).not.toBeInTheDocument();
  });

  it("shows an explicit empty artifact state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ schema_version: "1.0", items: [] }))
    );
    render(<Overview />);

    expect(await screen.findByText("No experiment artifacts are configured.")).toBeInTheDocument();
  });

  it("renders an accessible nonblank Pareto point", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ schema_version: "1.0", items: [experiment] }))
    );
    const { container } = render(<Pareto />);

    await waitFor(() => expect(container.querySelector(".plot-point")).toBeInTheDocument());
    expect(screen.getByLabelText("Quality and latency plot")).toBeInTheDocument();
  });
});