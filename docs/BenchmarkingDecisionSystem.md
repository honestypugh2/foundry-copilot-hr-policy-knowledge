# Benchmarking and Decision System

This document defines the evidence system. For pattern setup, source-file
ownership, smoke tests, and the relationship to the published and planned blog
posts, start with
[Pattern Setup, Code Ownership, and Benchmark Guide](PatternSetupAndBenchmarkGuide.md).

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

## Viewing Metrics and Gaps

The Benchmark Workbench is the index and decision surface; it does not replace
the native systems that own traces, production telemetry, load evidence, or
billing. Start the API and frontend in separate terminals:

### Gap this benchmark fills

Microsoft-native products provide deep evidence within their own boundaries,
but no single native view makes a controlled, apples-to-apples architecture
decision across Copilot Studio Pattern A, A2, B, C, and Hosted. The workbench
fills four cross-product decision gaps:

1. **Cross-pattern comparison:** maps every pattern and Hosted retrieval mode
  into one normalized experiment contract.
2. **Compatibility enforcement:** refuses to rank runs with different datasets,
  corpora, indexes, models, retrieval modes, or execution boundaries as though
  they were equivalent.
3. **Release qualification:** joins deterministic quality and security with
  latency, reliability, estimated variable cost, sample sufficiency, Pareto
  membership, and SLO gates.
4. **Missing-evidence visibility:** preserves measured, fixture-only,
  run-required, and unavailable states instead of turning gaps into zeros or
  implied proof.

This is an augmentation layer, not a replacement monitoring product. Copilot
Studio remains the employee entry point and orchestration surface. Application
Insights and Grafana own production traces, trends, dashboards, and alerts.
Foundry owns evaluation and agent drill-down. Azure AI Search owns retrieval
capacity and throttling. Azure Load Testing owns concurrent-load evidence, and
Azure Cost Management owns billed cost.

### Integration lifecycle

| Stage | Lead system | How the systems work together |
| --- | --- | --- |
| **Design** | Benchmark workbench | Keep candidate patterns as separate Copilot Studio routes or test agents. Run the same versioned HR cases and capture normalized results plus native trace/evaluation correlation IDs. |
| **Release** | Benchmark workbench | Compare only compatible baseline and candidate runs. Apply quality, security, p95, reliability, cost, sample, and SLO gates before changing the production route, prompt, model, index, or retrieval mode. |
| **Production** | Microsoft-native services | Copilot Studio serves users. Use Application Insights, Grafana, Foundry, Search, Load Testing, and Cost Management for live operations and root-cause analysis. The workbench links to these systems but does not copy their detailed views. |
| **Improve** | Both | Convert representative production failures, slow cases, and retrieval misses into sanitized controlled cases. Rerun candidates and qualify the fix before release. |

Do not stream arbitrary production telemetry into controlled benchmark
percentiles. Correlate by experiment, run, case, operation, and time window;
then preserve the separate evidence boundaries.

### Run the workbench

```bash
source .venv/bin/activate
ENABLE_TRACING=false \
BENCHMARK_ARTIFACT_DIR="$PWD/experiments/reports" \
python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000
```

```bash
cd src/frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5174`. The Vite development server proxies `/api` to
the backend on port `8000`.

| Question | View | Evidence boundary |
| --- | --- | --- |
| Which controlled runs exist? | Workbench **Experiments** or `GET /api/benchmarking/experiments` | Normalized local report artifacts |
| What did one run measure? | **Experiment detail** or `GET /api/benchmarking/experiments/{id}` | Latency distribution and categories, success/error/throttle, quality, security, calibrated judges, estimated cost, and provenance |
| Which runs are comparable? | **Compare** | Fails closed when manifest scope fields differ |
| Which option passes current gates? | **Pareto / SLO** | Quality, p95 latency, success, security, variable-cost, sample, and provenance gates |
| Which evidence stays here versus Microsoft-native? | **Evidence coverage** | Normalized decision evidence versus authoritative operational detail, with investigation guidance |
| What is implemented in the repository? | `GET /api/benchmarking/capabilities` | Executable Microsoft asset-reuse registry remains API-accessible; the full inventory is intentionally not duplicated in the frontend |
| Where are detailed traces and tokens? | **Operations** to Application Insights and Foundry | Native trace/evaluation systems remain authoritative |
| Where are Search capacity and failures? | `experiments/kql/` in Azure Monitor or Log Analytics | Time-bounded production telemetry, separate from controlled rows |
| Where are load results? | **Operations** to Azure Load Testing | Never merge load rows into sequential benchmark percentiles |
| Where is billed cost? | **Operations** to Azure Cost Management | Shared-resource billing; not per-request attribution |
| What exactly was committed? | `experiments/reports/<publication>/` | Sanitized manifest, JSONL rows, JSON/Markdown report, and evaluation summary |

The workbench visualizes the aggregate fields currently available for the
architecture decision. Per-invocation TTFT, TTLT, stream duration, token usage,
references, activity, response IDs, and trace IDs remain in sanitized JSONL or
their authoritative native trace system; they are not copied into aggregate
charts when the provider did not expose an aggregate. An empty stage, activity,
or cold/warm section means unavailable, not zero.

### Alignment with the blog evidence gate

The app is a decision surface for available evidence, not proof that every
planned blog figure is complete. Current alignment is:

| Blog evidence requirement | Current app/evidence status |
| --- | --- |
| Architecture boundaries | **Available:** A, A2, B, C, and Hosted show automation, telemetry, implementation, and evidence state. Microsoft-native Preview/GA status appears on Operations destinations; the verification date remains in documentation. |
| Manifest compatibility and provenance | **Available across surfaces:** Compare fails closed on incompatible scope; Experiment detail shows user-relevant run configuration; complete commit/environment provenance remains in the committed manifest and report rather than a standalone frontend tab. |
| Quality by category | **Pending:** overall deterministic quality/security and supplemental judge calibration are available, but the aggregate contract does not yet contain category-level quality. |
| p50/p95/p99 latency | **Available:** experiment detail shows client wall-time percentiles, sample count, boundary, and small-sample caveats. Confidence intervals are not yet part of the aggregate contract. |
| Reliability and throttling | **Partial:** controlled success/error/throttle rates are available; bounded production or isolated load evidence remains pending. |
| Cost | **Partial:** versioned variable model-cost estimates are available; dated billed-cost reconciliation remains pending in Azure Cost Management. |
| Pareto/SLO | **Available:** qualification failures, publication blockers, and Pareto membership are visible. |

The blog remains gated on category-level quality, confidence limits, explicit
failure counts, connected production/load evidence, and billed-cost
reconciliation. The frontend must not infer or fabricate those fields.

The overview helps users choose an architecture for the HR policy assistant. It
combines the five architecture paths, the three Hosted retrieval modes,
controlled benchmark evidence, evidence gaps, and links to the Microsoft
systems that own operational detail. The 2026-08-10 publication shows
deterministic quality of 100% for tool retrieval and 85.7% for both semantic
and agentic context. Pattern A is visible as fixture-only evidence; Pattern C
is visible as an implemented adapter that still requires a comparable
controlled run. A fixture value is never presented as Azure performance
evidence.

Compact tables render an em dash for an unavailable value instead of repeating
"Not measured" across every row. Experiment detail and evidence guidance retain
the measurement boundary, configuration state, and authoritative destination
so absence remains explicit and is never confused with zero.

## Reading Latency Percentiles

Experiment detail reports client-observed end-to-end response time. Lower is
better. Compare percentiles only when the dataset, corpus, index, model,
retrieval mode, execution boundary, and other compatibility fields match.

| Metric | Plain-language meaning | How to use it |
| --- | --- | --- |
| **p50** | The median: 50% of requests completed at or below this time and 50% took longer. It is not the average. | Represents the typical request. |
| **p95** | 95% completed at or below this time; the slowest 5% took longer. | Primary tail-latency signal for user experience and SLO qualification. |
| **p99** | 99% completed at or below this time; the slowest 1% took longer. | Highlights extreme tail behavior, but is sensitive to individual slow cases in small samples. |

For example, p95 of `25,758 ms` means 95% of measured requests completed in
about 25.8 seconds or less. It does not mean every request took 25.8 seconds.
Always read p50/p95/p99 with sample count, success rate, and the measurement
boundary. Reports warn when fewer than 30 samples make percentile estimates
unstable; even with 35 samples, one slow observation can move p99 materially.

## Qualification Profiles

The decision API defaults to the **Copilot front-door release profile** below.
These are project acceptance criteria for this HR assistant, not Microsoft
service guarantees. Review them with product and operations owners before a
production release.

| Gate | Release threshold | Rationale |
| --- | ---: | --- |
| Deterministic quality | at least 85% | Allows at most one miss in the seven-case release set while keeping failed categories visible. Expand the dataset before treating this as a mature quality target. |
| Copilot Studio client p95 | at most 30 s | The employee-facing tail target is set just above the measured Hosted development distribution. It includes Copilot orchestration, retrieval, and synthesis when the Direct Line boundary is used. |
| Success rate | at least 99% | Release point-estimate gate. With only 35 samples, zero observed failures has a 95% Wilson lower bound near 90%; use the isolated load profile and production telemetry for a tighter reliability claim. |
| Security pass rate | 100% | Any deterministic prompt-injection or secret-disclosure failure blocks release. |
| Estimated variable model cost | at most USD 0.05/request | A project budget guard for complete service-reported token usage. Shared Search, Copilot licensing, hosting, and observability charges remain separate. |

For direct component diagnostics, use **p95 at most 2 s**, **success at least
99%**, and **zero observed throttles**. Do not put component and Copilot
front-door candidates on one Pareto frontier. Component runs identify where
time or failures originate; only complete Copilot Studio runs qualify the
employee experience.

The workbench produces no recommendation when front-door evidence,
category-level deterministic quality, rate confidence intervals, explicit
outcome counts, security, or variable-cost evidence is missing. A Pareto point
without those publication gates is exploratory, not a release recommendation.

## Operations Investigation Guide

The **Operations** page is a handoff from normalized benchmark evidence to the
Microsoft service that owns the detailed telemetry. A **Link available** badge
means only that an approved destination URL is configured. It is not a service
health indicator and does not prove that matching telemetry exists.

### Application Insights: latency, failures, and traces

Use Application Insights when a controlled run is slower, fails, or follows an
unexpected model or tool path:

1. Select the benchmark time range and a comparable earlier window.
2. Open **Performance**, select the operation, and compare duration, request
  count, and failures.
3. Open a slow sample in end-to-end transaction details and identify the
  longest dependency or span.
4. Filter by experiment, run, case, operation ID, or custom dimensions when
  those correlations were recorded.
5. Use **Agents (Preview)** token and tool-call charts to investigate a possible
  cause. Token spikes can correlate with latency, but do not prove a latency
  regression by themselves.

### Other authoritative systems

| Destination | Use it when | Inspect and interpret |
| --- | --- | --- |
| **Azure Managed Grafana** | A latency or reliability change may be sustained across time, traffic, or resources. | Compare p95 with volume, failures, throttling, dependencies, alerts, and deployment annotations; open Application Insights for an individual trace. |
| **Microsoft Foundry** | Quality, task adherence, relevance, groundedness, or tool behavior changes. | Compare aggregate evaluations, inspect failed rows and linked traces, and treat model judges as supplemental to deterministic gates. |
| **Azure AI Search** | Retrieval is slow, throttled, incomplete, or competing with ingestion. | Compare Search latency with query volume, throttling, capacity, indexer activity, and skillset work for the same resource and time window. |
| **Azure Load Testing** | Concurrent-user behavior, throughput, or saturation must be measured. | Confirm the identical load profile, then read throughput, failures, and p95/p99 together. Keep load distributions separate from sequential controlled runs. |
| **Azure Cost Management** | Benchmark estimates must be reconciled with billed Azure cost. | Scope to the same subscription, resource group, currency, and billing period. Separate shared infrastructure and record any allocation rule; do not claim shared monthly cost as per-request attribution. |

## Current Cost Evidence

### Two cost lanes, never one axis

Cost is measured in **two non-interchangeable lanes**, and the decision system
keeps them separate rather than forcing a single number:

| Lane | Patterns | Unit | Source | Where it shows |
| --- | --- | --- | --- | --- |
| **Foundry per-token USD** | B, Hosted (tool / context-semantic / context-agentic), run locally with the Agent Framework adapter | USD per invocation, estimated from service-reported input/cached/output tokens × a dated retail pricing profile | SDK final aggregated usage × pricing profile | `estimated_variable_cost` populated; plotted and gated |
| **Copilot Studio per-message Credits** | A, A2, C, and the B/Hosted front doors | Copilot Studio message **Credits** (not tokens, not USD-per-token) | Copilot Studio **Operate → Cost** / Power Platform Admin | `estimated_variable_cost` stays `null` by design; Credits reported out-of-band |

A `null` variable cost on a Copilot Studio front-door run is **correct, not
missing evidence** — that lane is not token-metered, so it can never join the
Foundry per-token axis. Do not impute a per-token USD figure for a Copilot
Studio pattern, and do not treat a Copilot Studio Credit as comparable to a
Foundry token cost. Compare cost **within a lane**; state the lane before any
cross-lane cost remark.

### Deployed hosted-endpoint limitations

The deployed Foundry hosted agent (`foundry_hosted_agent` boundary) returns an
answer and citations but **does not surface per-token usage or KB retrieval
activity** through the response, and its Application Insights resource currently
carries **no `gen_ai` spans** (the deployed agent is not wired with an
`APPLICATIONINSIGHTS_CONNECTION_STRING`). Consequences:

- Deployed hosted runs record quality and security but keep
  `estimated_variable_cost` `null`; their variable cost is represented by the
  **local** Agent Framework re-run of the same retrieval mode, which is
  token-instrumented and priced.
- **Agentic phase timings** (query planning → parallel search → merge/rank) are
  only available on the A2 front-door harness and the **local** Hosted runs, not
  on the deployed endpoint.
- Token/cost backfill from App Insights is not feasible while the workspace is
  empty; the local re-run is the authoritative per-token evidence and is treated
  as cost-equivalent to the deployed agentic mode.

### Pricing profile

The versioned
[cache-aware GPT-5 Mini Global Standard pricing profile](../experiments/pricing/azure-gpt-5-mini-global-standard-cache-aware-2025-08-01.json)
records Azure public retail input, cached-input, and output meters, meter IDs,
effective date, and source query for the `gpt-5-mini` `2025-08-07` deployment.
These are estimates from public retail rates, not billed-cost data; Azure Cost
Management remains authoritative for billed cost.

The Agent Framework adapter now consumes usage from the SDK's final aggregated
stream response and prices it only when the manifest names the loaded profile
and all required quantities are `service_reported`. Reports distinguish mean
variable cost per invocation from run total. The curated 2026-08-10 publication
contains 35 fully priced invocations for each of the tool, context-semantic, and
context-agentic modes.

The profile excludes Search capacity, agentic retrieval reasoning, evaluator
usage, and other shared or fixed charges. Actual Azure charges are reconciled
separately in Azure Cost Management because shared resources cannot be
attributed reliably per request.

For a profiled run, set the manifest value to
`azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` and pass:

```bash
--pricing-profile experiments/pricing/azure-gpt-5-mini-global-standard-cache-aware-2025-08-01.json
```

The runner rejects a missing or mismatched profile and keeps cost unavailable
when token quantities are absent or are not service-reported.

## Observability Alignment and Gaps

The implementation was checked on 2026-08-10 against the Microsoft article
"Built-In Observability for Serverless AI Agents on Azure Functions" and the
two benchmark examples referenced in the project review.

| Area | Status | Repository evidence or recommendation |
| --- | --- | --- |
| Agent/model/tool traces | **Aligned, connected proof pending** | Agent Framework native OpenTelemetry spans export through `src/observability/tracing.py`; benchmark baggage correlates experiment, configuration, run, and case. Verify one deployed trace tree before publication. |
| Incompatible AI client wrapper | **Fixed** | All Agent Framework hosts disable `AIProjectInstrumentor` and OpenAI auto-instrumentation while retaining OpenTelemetry export. A focused test prevents regression. |
| Request and response model | **Partial** | KQL reads `gen_ai.response.model`, matching the blog's Model Router guidance. Add a connected assertion that request deployment and actual response model are both present. |
| Session correlation | **Gap** | Benchmark runs have run/case correlation, but interactive chat does not yet pass a stable Agent Framework session. Add a per-conversation session ID and propagate it to API results and spans. |
| Latency | **Aligned** | Reports separate client wall time, service time, TTFT, TTLT, stream duration, stage spans, and provider activity. Never reconstruct one boundary from another. |
| Token and variable cost | **Aligned for new runs** | Input/output usage comes from the final service response; named dated rates and unit conversion produce estimated mean and total cost. Reasoning tokens remain visible and must not be double charged when included in output usage. |
| Billed cost | **Gap by design** | Azure Cost Management is authoritative. Add a dated subscription/resource-group export and reconciliation report; do not allocate shared Search, hosting, Grafana, or monitoring charges per request without a declared allocation rule. |
| Sensitive content | **Aligned** | Prompt, completion, and tool-argument recording is off by default for HR privacy. |
| Sampling and flush | **Benchmark fixed; production policy gap** | Controlled benchmark tracing uses a `1.0` sampling ratio and the CLI flushes tracing on exit when enabled. A declared production sampling policy remains pending. |
| Dashboards and alerts | **Gap** | Application Insights, Log Analytics, Search diagnostics, and Managed Grafana are provisioned, but dashboard JSON and alert rules are not versioned in IaC. Add p95 latency, failure/throttle, missing-usage, and cost-estimate coverage alerts. |

The Model Router demo is useful for reading the actual `response.model`, timing
the request, and calculating token cost. Its fallback prices and conversion of
missing usage to zero are suitable for a demo but are deliberately not copied
here. The Foundry hill-climbing example supplies the stronger benchmark rule:
compare the complete model/prompt/reasoning package on held-out quality,
latency, and token cost, while tracking hosting cost separately.

## Completion Status

1. **Complete:** verified Azure CLI identity and deployed GPT-5 Mini version/SKU.
2. **Pending:** connected trace smoke test proving the complete deployed span
   tree and response-model attributes in Application Insights.
3. **Partial:** benchmark sampling/flush is implemented; stable interactive
   sessions plus versioned Grafana dashboards and Azure Monitor alerts remain.
4. **Complete:** reran tool, context-semantic, and context-agentic from clean
   commit `9c94215`, with 35 measured cases and declared warmups each.
5. **Pending by design:** publish an approved estimate-versus-billed
   reconciliation without falsely allocating shared fixed costs per request.
6. **Complete for the current publication:** attached deterministic quality and
   security gates, structured supplemental judge scores, and calibration.
7. **Pending:** isolated load execution and approved production SLOs. The
   workbench already fails closed on comparability, evidence, and publication
   gates.

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
| Foundry RAG evaluators | **Adapter** | The current publication uses structured Foundry Responses API judges and records evaluator tokens plus deterministic calibration; native evaluator reports still require normalization. |
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
| 3. Quality and regression | **Publication evidence complete** | Deterministic quality/security gates and paid structured judge calibration are attached to the current three-mode publication. |
| 4. Load and scalability | **Harness complete; execution deferred** | Locust input/output is isolated from controlled experiments and remote targets require explicit non-production confirmation. |
| 5. Production correlation | **Offline complete; connected validation pending** | Benchmark baggage is copied onto existing SDK spans without duplicate spans; bounded KQL templates cover latency, failures, token correlation, evaluation, and Search capacity. |
| 6. Cost, Pareto, and SLO | **Offline complete** | Versioned user pricing, fixed/variable separation, Pareto selection, and fail-closed SLO qualification have deterministic tests. |
| 7. Documentation/blog evidence | **Partial; publication still gated** | Clean 35-case reports are committed. Category-level quality, confidence limits, explicit failure counts, connected production/load evidence, alerts, and billed-cost reconciliation remain pending. |
| 8. React workbench | **Complete for available contracts and locally validated** | The artifact-backed BFF and React app expose list, aggregate detail with contextual provenance, compare, pattern evidence, Pareto/SLO, evidence ownership, and native-link guidance. The full capability registry remains available through the API rather than a frontend inventory. |

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