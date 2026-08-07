# Benchmarking and Decision System

This repository uses one normalized experiment contract to compare HR policy
patterns without treating controlled runs, load tests, and production telemetry
as interchangeable evidence. The first executable slice is in
`src/benchmarking`; it wraps the existing direct classic Search call through
dependency injection and does not change production routing.

## Evidence Rules

- **Controlled experiment:** sequential or explicitly configured concurrent
  cases run against a recorded manifest. Use these results for reproducible
  pattern and configuration comparisons.
- **Load/capacity test:** concurrent traffic with a named target, load profile,
  and saturation signals. Do not merge these rows into sequential latency
  distributions.
- **Production telemetry:** observed user traffic in Application Insights,
  Foundry, Azure AI Search, and Azure Monitor. Use the native products for
  detailed investigation and link normalized summaries back to them.
- A latency is **measured** only when a committed result records its manifest,
  sample count, environment, and measurement boundary. Values such as
  `~1-2 s` and `~10-14 s` elsewhere in this repo remain illustrative.
- Client wall time, service-reported elapsed time, and child-span duration are
  separate metrics. Missing values are `null` with a reason, never zero or a
  reconstructed duration.
- Pattern C qualifies on deterministic locator behavior and verbatim source
  URLs. It is not assumed to outperform Pattern A without measured p95 evidence
  from comparable manifests.

## Microsoft Asset Reuse Matrix

Status and interfaces were verified against current Microsoft documentation on
2026-08-03. Preview connectors must advertise that status and degrade cleanly.

| Capability | Classification | Repository responsibility |
| --- | --- | --- |
| Application Insights Agent details (Preview) | **Reuse** | Authoritative trace, token, tool-call, latency, and error investigation; future workbench links to it. |
| Application Insights dashboards with Grafana | **Reuse** | Operational dashboards and alert-oriented charts; keep dashboard resources in IaC where supported. |
| Foundry Agent Monitoring and evaluation reports | **Reuse** | Production monitoring and optional cloud evaluation; local deterministic evaluation remains available. |
| Azure Search OpenAI Demo and Locust | **Reuse** | Follow workload conventions and run Locust directly; do not vendor the demo. |
| Azure AI Search classic query response | **Adapter** | Record client wall time and service `elapsed-time` separately when the active SDK boundary exposes headers. |
| Azure AI Search Knowledge Base retrieve | **Adapter** | Map the GA `2026-04-01` response and opt-in preview versions into normalized references and lossless activity records. |
| Foundry Agent Service plus MCP | **Adapter** | Normalize the actual invocation, response usage, and trace IDs; never issue a second retrieve to infer MCP timing. |
| Pattern C and Hosted Agent call sites | **Adapter** | Reuse existing routes and agent protocol, preserving deterministic and cold-start semantics. |
| Copilot Studio A/A2/B/C/Hosted | **Adapter** | Run published development agents through Direct Line or import external captures; identify Copilot-owned generation as outside repo instrumentation. |
| RAG Experiment Accelerator | **Reuse** | Use for retrieval sweeps and exchange datasets/results where stable contracts justify an adapter. |
| Foundry RAG evaluators | **Adapter** | Optional evaluator backend; report evaluator tokens and calibrate against deterministic checks and a reviewed gold set. |
| Foundry/OpenTelemetry tracing | **Adapter** | Add low-cardinality experiment/configuration attributes to existing spans with content recording off by default. |
| Azure Monitor and Search diagnostic KQL | **Reuse** | Query authoritative spans, service duration, throttling, query rate, and ingestion contention. |
| Azure Cost Management | **Reuse** | Authoritative billed-cost destination; normalized estimates use user-supplied, versioned pricing profiles. |
| Normalized contracts, comparison, regressions, Pareto, and SLO qualification | **New gap coverage** | Join comparable evidence and explain which requirements each architecture satisfies. |
| Read-only benchmark decision workbench | **New gap coverage** | Present cross-product decisions and deep links without recreating native trace, evaluation, dashboard, or billing products. |

## Phase 1 Usage

`ExperimentManifest`, `CaseResult`, and `AggregateReport` are strict Pydantic
contracts with schema version `1.0`. Provider activity permits unknown fields
so new Knowledge Base activity types survive serialization. Retrieval
references contain stable source IDs and omit policy content by default.

The direct Search adapter accepts a callable compatible with
`IntegratedVectorizationSearchService.search(query, top)`. The runner emits
normalized rows, and `reporting.py` writes JSONL plus JSON and Markdown
aggregates. Percentiles use deterministic linear interpolation over sorted
observations. Reports warn when fewer than 30 measured samples make percentile
estimates unstable.

Run the offline validation with:

```bash
source .venv/bin/activate
pytest tests/test_benchmarking_phase1.py -q
```

Run the sanitized CLI smoke experiment with:

```bash
source .venv/bin/activate
python -m src.benchmarking.cli \
  --manifest experiments/manifests/synthetic-direct-search.json \
  --cases experiments/datasets/synthetic-migration-smoke.json \
  --fixture-responses experiments/datasets/synthetic-direct-search-responses.json \
  --output-dir experiments/reports/synthetic-direct-search
```

Fixture mode validates contracts and report generation only. Its local wall
times are not Azure performance evidence and must not be used in pattern
recommendations.

For exported real pattern-agent setup, per-agent manifest generation, and Direct
Line execution, see
[CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md).

## Implementation Roadmap

| Phase | Status | Validation boundary |
| --- | --- | --- |
| 1. Contracts and direct Search report | **Complete** | Fake-backed offline contract, timing, percentile, JSONL, JSON, and Markdown tests. |
| 2. Remaining pattern adapters | **Offline complete** | Foundry/MCP, Hosted, Pattern C, and Copilot import have credential-free contract tests; live smoke requires credentials and permission. |
| 3. Quality and regression | **Offline complete** | Eight-category retrieval metrics and deterministic citation/refusal graders are integrated; paid Foundry evaluation remains optional. |
| 4. Load and scalability | **Harness complete; execution deferred** | Locust input/output is isolated from controlled experiments and remote targets require explicit non-production confirmation. |
| 5. Production correlation | **Offline complete; connected validation pending** | Benchmark baggage is copied onto existing SDK spans without duplicate spans; bounded KQL templates cover latency, failures, token correlation, evaluation, and Search capacity. |
| 6. Cost, Pareto, and SLO | **Offline complete** | Versioned user pricing, fixed/variable separation, Pareto selection, and fail-closed SLO qualification have deterministic tests. |
| 7. Documentation/blog evidence | **Outline complete; measured claims pending connected runs** | Existing pattern ambiguity is corrected; publish comparisons only from committed environment-specific reports. |
| 8. React workbench | **Complete and locally validated** | The artifact-backed BFF, generated contracts, normalized provider views, list/detail/compare/pattern/capability routes, and fail-closed native links are covered by component and browser tests. |

Phase 8 validation covers desktop and mobile workflows, accessibility, overflow,
nonblank Pareto rendering, and the production frontend build. Vite uses port
`5174` by default. These checks validate presentation and contracts; they are
not connected Azure performance evidence.

No Azure deployment, paid evaluation, remote load test, or Agent Optimizer job
is implied by an offline-complete phase. Connected validation remains gated by
an approved non-production deployment plan.

## Current API Boundaries

- Azure AI Search agentic retrieval has GA capabilities in REST API
  `2026-04-01`. Examples that require `2026-05-01-preview` must be labeled and
  enabled separately.
- Knowledge Base responses expose `response`, `activity`, and `references`.
  Known activity types are normalized when useful; unknown records remain
  lossless.
- Application Insights Agent details is Preview as of the verification date.
- Foundry Agent Monitoring dashboard views are Preview as of the verification
  date; Application Insights and the connected Log Analytics workspace remain
  the telemetry stores of record.
- Detailed traces remain in Agent details. Grafana is the destination for
  custom operational dashboards, not a trace explorer to reproduce in React.

See [ReactBenchmarkWorkbenchADR.md](ReactBenchmarkWorkbenchADR.md) for the
native-versus-custom product boundary and
[BenchmarkingBlogOutline.md](BenchmarkingBlogOutline.md) for the publication
evidence gate.