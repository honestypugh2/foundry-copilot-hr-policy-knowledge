---
name: expand-hr-policy-benchmarking
description: "Implement evidence-based latency, quality, cost, load, and production-observability comparisons across the HR policy repo's retrieval and agent patterns while reusing Microsoft benchmark assets."
disable-model-invocation: true
argument-hint: "Optional scope, target patterns, environment constraints, or acceptance thresholds"
---
# Implement the HR Policy Pattern Benchmark and Decision Guide

Work in the current clone of:

- https://github.com/honestypugh2/foundry-copilot-hr-policy-knowledge

The user's optional scope or constraints are:

> ${input:scope:Implement the smallest complete vertical slice, then continue through the phases that can be validated in the current environment.}

## Objective

Expand this existing repository and its existing blog story. Do not create a separate benchmark repository unless the implementation proves that a reusable package is needed by a second application.

Turn the repository's A, A2, B, C, and Hosted pattern guidance into an executable, reproducible decision system that answers:

> Which retrieval and agent architecture satisfies this workload's quality, latency, reliability, security, and cost requirements?

Use Microsoft tooling for the capabilities Microsoft already provides. Add only the adapter, experiment-contract, comparison, and decision-support functionality that remains missing.

The result must connect controlled development experiments to production telemetry without pretending that they are the same workload.

## Required Starting Behavior

Before editing:

1. Inspect the current branch and working tree. Preserve user changes.
2. Read the current `README.md`, `docs/RetrievalPatterns.md`, `docs/AgentArchitecturePaths.md`, `src/evaluation/`, `src/observability/`, `scripts/demo/`, tests, dependency files, and configuration models.
3. Locate the published blog link already associated with the repo and preserve its architecture narrative.
4. Verify current Microsoft documentation and sample interfaces rather than assuming the links or APIs in this prompt are unchanged.
5. State one falsifiable implementation hypothesis and the cheapest focused check that could disprove it.
6. Build the first vertical slice immediately after that local inspection. Do not map the entire repository before beginning.

If the current repository differs from this prompt, adapt to the repository and document the discrepancy. Do not overwrite newer working functionality to match stale assumptions.

## Architecture Recommendation

Use this repository as both:

- The executable HR policy reference application.
- The concrete pattern-comparison case study behind a follow-up blog series.

Add an experiment layer inside the repo, preferably following existing naming conventions. A reasonable shape is:

```text
experiments/
  manifests/
  datasets/
  reports/
  kql/
web/
  src/
    app/
    features/
    providers/
    shared/
src/
  benchmarking/
    adapters/
    api/
    providers/
    models.py
    runner.py
    aggregation.py
    costing.py
    reporting.py
```

Change this layout if the repo already has a better ownership boundary. Keep runtime application behavior independent from optional benchmarking dependencies.

Use a two-layer experience:

1. **Microsoft-native operational plane**: Application Insights Agent details, Azure Monitor Dashboards with Grafana, Foundry Agent Monitoring, Foundry evaluation reports, Azure AI Search monitoring, and Azure Cost Management remain the authoritative detailed experiences.
2. **Repo-owned decision plane**: a thin React Benchmark and Decision Workbench presents normalized experiments, pattern comparisons, regressions, Pareto trade-offs, SLO qualification, provenance, and links into those native experiences.

Do not build the React application until the first normalized contract-to-report vertical slice works. The frontend consumes that stable contract; it must not become another schema authority.

## Do Not Rebuild Microsoft Products

Use or integrate the following assets according to their actual strengths.

| Need | Microsoft asset to use | Integration expected in this repo |
|---|---|---|
| Unified agent runtime monitoring | [Application Insights Agent details](https://learn.microsoft.com/azure/azure-monitor/app/agents-view) | Use as the primary trace, latency, error, token, tool-call, model, and transaction investigation UI. Add deep links from the workbench. Do not recreate its trace explorer. Verify current preview status. |
| Custom operational dashboards | [Dashboards with Grafana in Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/grafana-dashboards) | Save repo-specific dashboards as Azure resources, manage them with RBAC and Bicep/ARM where supported, and link to them from the workbench. Prefer this before adding equivalent React charts. |
| Agent operational, evaluation, and red-team monitoring | [Foundry Agent Monitoring Dashboard](https://learn.microsoft.com/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard) | Use for production agent monitoring and continuous/scheduled evaluation where supported. Verify preview features and do not make them required for local experiments. |
| Realistic end-to-end RAG workload and benchmark conventions | [Azure Search OpenAI Demo](https://github.com/Azure-Samples/azure-search-openai-demo) | Link to its architecture and evaluation guidance. Reuse compatible conventions or small attributed portions only when license-compatible. Do not fork or vendor the application. |
| Concurrent load generation | The Azure Search OpenAI Demo's Locust harness and [Locust](https://locust.io/) | Add thin Locust tasks for this repo's HTTP-accessible routes. Keep load generation separate from the experiment runner. Document local and Azure Load Testing execution. |
| Direct agentic-retrieval timing contract | [Agentic retrieval quickstart](https://learn.microsoft.com/azure/search/search-get-started-agentic-retrieval) and language samples | Parse the official Knowledge Base `activity[]` response shape. Preserve unknown activity records and tolerate API-version additions. |
| Language-neutral direct baseline | [Azure Search REST samples](https://github.com/Azure-Samples/azure-search-rest-samples/tree/main/Quickstart-agentic-retrieval) | Provide a documented direct REST baseline or an adapter using the same API contract. Avoid UI and agent overhead in this baseline. |
| Foundry Agent plus MCP example | [Python agentic retrieval pipeline](https://github.com/Azure-Samples/azure-search-python-samples/tree/main/agentic-retrieval-pipeline-example) | Align the end-to-end adapter with Microsoft's supported agent/MCP invocation. Do not issue a second direct retrieval to infer timing for the MCP call. |
| Retrieval configuration experiments | [RAG Experiment Accelerator](https://github.com/microsoft/rag-experiment-accelerator) | Document how to use it for chunking/search/reranking sweeps. Add import/export interoperability if practical; do not recreate its sweep engine. |
| Quality and safety evaluation | [Foundry agent evaluation](https://learn.microsoft.com/azure/foundry/observability/how-to/evaluate-agent) and [RAG evaluators](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/rag-evaluators) | Add an optional Foundry evaluation backend while retaining deterministic local metrics needed for CI and offline tests. |
| Production traces | [Foundry tracing](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup), OpenTelemetry, and Application Insights | Add experiment and pattern attributes to existing spans. Keep prompt/tool content recording off by default. |
| Production latency diagnosis | Azure Monitor and the Microsoft GitHub Copilot for Azure latency KQL reference when currently available | Store adapted KQL templates with source attribution and schema notes. Query actual trace spans rather than reconstructed stages. |
| Search service capacity diagnosis | [Analyze Azure AI Search performance](https://learn.microsoft.com/azure/search/search-performance-analysis) | Document and include KQL for query rate, service duration, throttling, and ingestion contention. |
| Model latency interpretation | [Azure OpenAI latency guidance](https://learn.microsoft.com/azure/foundry/openai/how-to/latency) | Report TTFT, TTLT, token counts, and generation rate together. Do not call token-driven latency a service regression. |
| Foundry IQ cookbook scenarios | [Microsoft IQ Series](https://github.com/microsoft/iq-series) and [IQ Samples](https://github.com/microsoft/iq-samples) | Link to the relevant setup/evaluation examples. Add adapters only when they exercise a path present in this repo. |
| Optimization after architecture selection | Agent Optimizer in Microsoft Foundry | Add an optional export/integration path for eligible hosted agents and evaluation suites. Do not make preview optimizer APIs a core dependency. |

For every addition, label it in code or documentation as one of:

- **Reuse**: run the Microsoft asset directly.
- **Adapter**: translate this repo's pattern or result into a Microsoft-supported contract.
- **New gap coverage**: functionality not supplied by those assets.

Do not copy large blocks from Microsoft samples. Prefer links, commands, adapters, and compatible schemas. Preserve required notices and attribution for any reused code.

## Gaps This Implementation Must Address

The new code must focus on gaps not already solved end to end by the listed assets:

1. One versioned experiment manifest shared across this repo's patterns.
2. One normalized result envelope joining latency, quality, reliability, security, and cost.
3. Comparable adapters for direct Search, direct Knowledge Base retrieval, MCP/Prompt Agent, deterministic lookup, and Hosted Agent paths that are actually runnable from code.
4. Pattern and router comparison using the same corpus and query dataset.
5. Latency-quality-cost Pareto reporting rather than ranking by latency alone.
6. Correlation among experiment ID, evaluation run ID, response ID, conversation ID, and trace ID where APIs expose them.
7. Permission-aware and fail-closed evaluation.
8. Corpus/index/configuration provenance and retrieval-regression detection.
9. Clear separation of controlled experiments, load/capacity tests, and production monitoring.
10. Evidence-backed updates to the repo's pattern decision tree and blog guidance.
11. A thin, reusable decision workbench that joins these results without replacing Microsoft-native monitoring and investigation UIs.

Do not claim that a UI-only path such as Copilot Studio Pattern A or A2 is automated if no supported programmatic invocation exists. Mark it as manual, externally driven, or proxy-measured, and document the measurement boundary.

## Measurement Contract

Create typed, versioned models using the repo's current validation library. Prefer JSONL for row-level results and JSON plus Markdown for aggregate reports.

### Experiment manifest

Capture at least:

- Schema version and experiment ID.
- Timestamp, git commit, dirty-worktree indicator, and runner version.
- Dataset name/version and corpus/index fingerprint.
- Pattern, retrieval mode, invocation path, API version, and output mode.
- Model deployment and known model/version metadata.
- Retrieval reasoning effort: `minimal`, `low`, or `medium` only when supported by the selected API.
- Search SKU, replica/partition counts when discoverable without requiring management-plane access.
- Search configuration: semantic configuration, vector settings, `top`, output document/token limits, filters, and relevant knowledge-source settings.
- Prompt/agent/configuration version without recording secrets or sensitive content.
- Region/client location when known.
- Warm-up count, measured repetitions, concurrency, timeout, and random seed.
- Pricing profile name/version; never embed a supposedly universal live price.

### Per-case result

Capture at least:

- Experiment, run, case, pattern, and configuration IDs.
- Query category and expected behavior.
- Start time, end-to-end duration, status, and error classification.
- TTFT, TTLT, stream duration, output tokens, and tokens/second where the path streams and exposes usage.
- Retry count, throttling, partial-result status, timeout, and HTTP/service status where available.
- Retrieval references with stable source identifiers, not sensitive full content by default.
- Activity records exactly as returned plus normalized known fields.
- Input, output, reasoning, and evaluator tokens when exposed.
- Local deterministic metric results and optional Foundry evaluator results.
- Estimated variable cost plus `unknown`/`not_applicable` support.
- Trace, response, conversation, and evaluation IDs when exposed.

Use `null` plus a reason such as `not_exposed_by_mcp` for unavailable data. Never manufacture a stage duration.

### Aggregate report

Report:

- Count, success rate, error and throttle rates.
- p50, p95, p99, minimum, maximum, and mean end-to-end latency.
- TTFT/TTLT and token-normalized generation metrics when available.
- Cold and warm results separately.
- Recall@k, precision@k where labels support it, MRR, citation correctness/completeness, groundedness, answer correctness, refusal correctness, and router accuracy.
- Token distributions and estimated cost/query.
- Results by query category and pattern.
- Pareto-efficient configurations for quality, latency, and cost.
- Confidence intervals or explicit sample-size warnings.
- Environment and configuration provenance.

Do not add stage durations together as if parallel Search operations were sequential. Distinguish:

- Client-observed wall time.
- Service-reported elapsed time.
- Child-span duration.
- Unattributed wall time.

Avoid the label `orchestration overhead` unless the trace proves that attribution. Prefer `unattributed_wall_time_ms`.

## Pattern Adapters

Implement only adapters grounded in current repo call sites.

### Direct classic Search baseline

Measure keyword/vector/hybrid/semantic variants already supported by the repo. Capture the service `elapsed-time` header when available and client wall time separately.

### Direct Knowledge Base retrieve

Use the current GA API for the GA comparison and a separately identified preview configuration only when the user opts into preview capabilities.

Parse activity types such as:

- `modelQueryPlanning`
- Knowledge-source activities such as `searchIndex`
- `agenticReasoning`
- `modelAnswerSynthesis`

Allow unknown future activity types. Record source-specific parallel timings without summing them into a false critical path.

Compare appropriate combinations including:

- Classic hybrid/semantic Search.
- Minimal, extractive Knowledge Base retrieval.
- Low/medium effort only when supported and explicitly enabled.
- Extracted data versus answer synthesis where supported.

### MCP and Prompt Agent

Measure the actual agent invocation and its real trace spans. Current MCP tool responses may not expose separate Knowledge Base `activity[]` and `references[]` envelopes.

Therefore:

- Do not make a second direct retrieve call for diagnostic timing.
- Do not compare that second call as though it decomposes the first.
- Mark unavailable Search-internal decomposition explicitly.
- Use OTel spans, response usage, and client wall time that belong to the actual invocation.

### Deterministic Pattern C

Measure lookup latency, exact-match success, source-path correctness, ambiguity behavior, and router correctness. Record model tokens as `not_applicable`, not zero-cost, unless the full request path proves no model was invoked before routing.

### Hosted Agent

Support the current Agent Framework invocation protocol and retrieval modes present in the repo. Record container cold start separately from steady-state request latency.

### Copilot Studio Patterns A and A2

If these paths cannot be invoked by a supported automated API in the repo:

- Provide a documented manual measurement protocol.
- Provide an import schema for captured timing/evaluation rows.
- Clearly mark Copilot Studio-side model calls and orchestration as outside repo instrumentation.
- Do not describe Pattern A as having no LLM if Copilot Studio generates the answer. Say `no repo-owned backend model call` when that is the accurate boundary.

## Quality, Security, and Reliability Dataset

Extend the existing synthetic HR dataset rather than adding private policy data.

Include categories for:

- Direct fact and policy-number lookup.
- Multi-policy synthesis.
- Ambiguous employee terminology and synonyms.
- Document-location requests.
- No-answer and out-of-domain requests.
- Conflicting, superseded, or duplicate policy evidence.
- Citation and exact-source requirements.
- Multi-turn context and correction.
- Router boundary cases.
- Permission-allowed and permission-denied cases.
- Prompt injection or untrusted instructions inside retrieved content.
- Partial source failure and timeout scenarios that can be tested safely with fakes.

Keep a small human-reviewed gold set. Calibrate LLM-judge results against it and report disagreement. Never use an LLM judge as the sole authority for access-control or exact-citation correctness.

## Cost Model

Implement cost as a versioned, user-supplied pricing profile, not hardcoded marketing figures.

Separate:

- Fixed Search infrastructure cost.
- Search feature/request charges.
- Model input/output/reasoning tokens.
- Foundry/agent execution costs when defined.
- Functions or container compute.
- Copilot Studio message consumption where the user supplies the applicable licensing model.
- Application Insights ingestion and evaluation-model tokens.

Every estimate must include:

- Currency and effective date.
- Region or pricing scope.
- Formula and measured quantity.
- Assumptions and excluded costs.
- `unknown` for unavailable quantities.

Do not claim that a path is cheaper merely because some charges are hidden inside another product's licensing boundary.

## Agent Optimizer Boundary

Treat Agent Optimizer as an optional downstream optimizer, not the ultimate architecture solution.

When public, documented APIs are available and the current agent is eligible:

1. Export or map the hosted-agent evaluation dataset and rubric into the documented optimizer format.
2. Support instruction, skill/tool-description, or model optimization without changing the benchmark's ground-truth dataset.
3. Evaluate optimizer candidates through the same normalized result and held-out test set.
4. Record optimizer job, candidate, score, token cost, and deployed agent version IDs.
5. Require an explicit deployment action; never auto-promote from this benchmark.

Do not use Agent Optimizer to choose among deterministic lookup, direct Search, direct Knowledge Base, Copilot Studio, and hosted-agent architectures. Do not add a private-preview dependency to normal installation. If only private-preview/blog information exists, implement documentation and a stable extension interface, not speculative API calls.

## React Benchmark and Decision Workbench

Build a React application only for the cross-product decision gap. It is not a generic Azure portal, observability platform, trace viewer, evaluation service, or billing system.

### Product boundary

The workbench should answer:

- Which patterns and configurations were tested under the same dataset and environment?
- Which configurations meet the selected quality, latency, reliability, security, and cost thresholds?
- What changed between two commits, datasets, indexes, prompts, agents, or model deployments?
- Which configurations are Pareto-efficient rather than merely fastest?
- Is a metric measured, estimated, unavailable, or not applicable?
- Where should an operator go next in Application Insights, Grafana, Foundry, Search, Load Testing, or Cost Management?

The workbench should not:

- Reimplement Application Insights Agent details or end-to-end transaction search.
- Reimplement Grafana, KQL exploration, alert authoring, Foundry evaluation reports, Azure Load Testing, or Cost Management.
- Query Azure management or data-plane APIs directly from browser code.
- Store Azure credentials, connection strings, pricing secrets, prompt content, or retrieved policy content in browser storage.
- Infer missing telemetry or present estimates as billed cost.
- Add write, deploy, optimize, load-test, or production mutation actions in the first release.

Before implementing any proposed screen, run this discriminating check:

> Can Application Insights Agent details, a saved Grafana dashboard, a Foundry report, or the existing generated Markdown report already answer this question with an acceptable workflow?

If yes, add a summary and deep link rather than duplicating the native experience. If no, document the decision gap that justifies the custom screen.

### Recommended stack

Inspect the target repository first and reuse any established frontend stack. If none exists, default to:

- React with TypeScript and Vite.
- The current stable React Router for route ownership and shareable comparison URLs.
- TanStack Query for server-state loading, cancellation, retries, and cache invalidation.
- Fluent UI React v9 and its icon package for an accessible Microsoft-aligned operational interface.
- One established charting library selected after checking license, accessibility, bundle size, and support for percentile distributions, scatterplots, confidence intervals, and Pareto frontiers. Do not hand-roll chart primitives.
- Vitest and React Testing Library for unit/component tests.
- Playwright for critical desktop and mobile workflows, accessibility checks, screenshots, and nonblank chart verification.
- MSAL only when Entra authentication is required by the selected hosting model.

Do not add a state-management library until local UI state exceeds what route state, component state, and TanStack Query can manage. Do not add a frontend monorepo tool unless the target repository already uses one or a second independently deployable web package proves the need.

### Backend-for-frontend boundary

Expose a small, versioned, read-only API from the existing Python service or a separately owned API module if that better matches the target repo. Keep provider credentials and Azure SDKs server-side.

Use provider contracts such as:

```text
ExperimentProvider
TelemetryProvider
EvaluationProvider
LoadTestProvider
CostProvider
ResourceMetadataProvider
CapabilityProvider
```

Each provider must:

- Return normalized contract models rather than vendor response objects.
- Advertise capabilities, source version, freshness, and preview/GA status.
- Distinguish `available`, `unavailable`, `not_configured`, `not_authorized`, `not_applicable`, and `degraded` states.
- Preserve source IDs and authoritative deep links.
- Have contract tests with recorded synthetic fixtures that contain no secrets or private content.
- Be replaceable when Microsoft APIs or schemas change without rewriting feature components.

Suggested read-only endpoints, adjusted to existing API conventions:

```text
GET /api/benchmarking/capabilities
GET /api/benchmarking/experiments
GET /api/benchmarking/experiments/{experiment_id}
GET /api/benchmarking/comparisons?baseline={id}&candidate={id}
GET /api/benchmarking/patterns/{pattern}/summary
GET /api/benchmarking/links/{resource_type}/{source_id}
```

Do not proxy arbitrary KQL or arbitrary Azure resource IDs from the browser. Use allowlisted query templates and resource scopes. Apply bounded time ranges, pagination, response-size limits, timeouts, and cancellation.

### Authentication and authorization

- Use Entra ID for deployed access and preserve an explicit local-development mode backed only by synthetic/local artifacts.
- Authenticate the SPA to the backend; do not put management-plane tokens in application code or configuration.
- Prefer managed identity for backend-to-Azure access.
- Do not assume that the backend's managed identity automatically preserves each user's Azure RBAC. Enforce application roles/groups and configured resource scopes, or use a documented delegated/on-behalf-of design only where the downstream API supports it.
- Fail closed when authorization cannot be established.
- Keep telemetry content recording disabled by default and redact sensitive fields at ingestion and API serialization boundaries.

### Information architecture

Build a work-focused application rather than a marketing dashboard. Use restrained density, stable tables, filters, and linked detail views. Do not use nested cards, oversized hero sections, decorative gradients, or card grids for every metric.

Required routes:

1. **Overview**: active environment, data freshness, capability status, SLO pass/fail summary, and recent regressions.
2. **Experiments**: filterable table with dataset, commit, corpus/index fingerprint, pattern, model, status, and timestamp.
3. **Experiment detail**: provenance, aggregate metrics, category breakdown, unavailable-data reasons, and source links.
4. **Compare**: baseline/candidate selection, absolute and relative deltas, confidence/sample warnings, and regression annotations.
5. **Patterns**: A/A2/B/C/Hosted evidence matrix with automation and telemetry boundaries.
6. **Pareto and SLO**: quality-latency-cost scatterplot/frontier plus explicit threshold controls and qualifying configurations.
7. **Operations**: summary-only production signals with deep links to Agent details, Grafana, Foundry, Search, and Load Testing.
8. **Data and provenance**: dataset, corpus, index, prompt, configuration, pricing-profile, and schema versions.

Required interaction behavior:

- Encode filters and comparison selections in the URL.
- Show units, sample count, time window, source, freshness, and measurement type with each metric.
- Never render unavailable values as zero.
- Pair charts with accessible tables and downloadable normalized data.
- Provide loading, empty, partial, unauthorized, stale, and provider-degraded states.
- Use server pagination or virtualization for row-level results.
- Keep desktop and mobile layouts usable without overlapping controls or truncated identifiers.
- Use native deep links for detailed traces, evaluation reports, dashboards, and Azure resources.

### Modularity and change tolerance

- Generate or share frontend TypeScript types from the versioned JSON schema instead of manually maintaining duplicate models.
- Keep API transport models out of visual components; map them through feature-level selectors/view models.
- Maintain a capability registry so preview features disappear or degrade cleanly rather than breaking routes.
- Put provider-specific API versions and mappings in backend adapters, not React components.
- Add schema compatibility tests for the current and immediately previous supported contract versions.
- Instrument the workbench itself with OpenTelemetry without capturing report contents or policy text by default.
- Keep feature flags typed, documented, and removable; do not scatter environment checks through components.
- Record Microsoft documentation verification dates for preview-dependent connectors.

## Step-by-Step Implementation

Work incrementally. After each substantive edit, run the narrowest executable validation before continuing.

### Phase 1: Contract and one vertical slice

1. Add typed manifest, per-case result, activity record, metric, pricing, and aggregate-report models.
2. Add JSON schema/versioning and serialization tests.
3. Implement the direct Knowledge Base adapter or direct Search adapter, whichever has the clearest existing call site.
4. Run a small fake-based test dataset through it.
5. Emit JSONL and a concise Markdown report.

Acceptance:

- No Azure credentials required for unit tests.
- Unknown activity types round-trip without loss.
- Missing metrics remain explicitly unavailable.
- p50/p95/p99 calculations have deterministic tests.

### Phase 2: Existing pattern adapters

1. Add adapters for current runnable classic Search, Pattern B/MCP, Pattern C, and Hosted paths.
2. Reuse existing orchestrators and demo entry points; do not duplicate business logic.
3. Add manual/import support for non-automatable Copilot Studio paths.
4. Add fake-based adapter contract tests.
5. Add at most a small opt-in live smoke suite, clearly marked and skipped by default.

Acceptance:

- The same case schema runs across adapters.
- A benchmark invocation does not change production routing.
- MCP diagnostics do not issue duplicate retrieval.

### Phase 3: Quality and regression evaluation

1. Adapt existing deterministic graders to the normalized result.
2. Add retrieval/citation/router/security metrics missing from current tests.
3. Add an optional Foundry evaluation backend following current Microsoft guidance.
4. Add export/import interoperability for RAG Experiment Accelerator or explain why a documented workflow is more maintainable.
5. Add dataset and corpus fingerprints.

Acceptance:

- CI can run useful evaluation without cloud access.
- LLM judges are optional and their token cost is reported.
- Security assertions use deterministic checks.

### Phase 4: Load and scalability

1. Add thin Locust tasks for HTTP-accessible repo patterns, following the Azure Search OpenAI Demo conventions.
2. Include smoke, baseline, and stress profiles, with user-controlled spawn rate and duration.
3. Document execution through local Locust and Azure Load Testing.
4. Keep load results separate from sequential experiment results, but provide a shared aggregate import.
5. Record failures, throughput, concurrency, p50/p95/p99, and saturation signals.

Acceptance:

- Locust is an optional dependency group.
- The load test cannot accidentally run against production without an explicit target/confirmation mechanism.
- No secrets are stored in Locust files or reports.

### Phase 5: Production observability correlation

1. Extend existing OTel spans with low-cardinality experiment/configuration attributes.
2. Keep sensitive content recording off by default.
3. Add attributed KQL templates for conversation percentiles, span bottlenecks, token/latency correlation, failures, Search service duration, throttling, and ingestion contention.
4. Document clock and attribution differences between client timing, Search diagnostics, and traces.
5. Add a production trace-to-evaluation-dataset workflow using current Foundry guidance.

Acceptance:

- High-cardinality IDs are queryable but not incorrectly emitted as metric dimensions.
- KQL files state expected tables and schema assumptions.
- Production telemetry is not required for local benchmark tests.

### Phase 6: Cost, Pareto analysis, and decision evidence

1. Add the versioned pricing-profile loader and cost formulas.
2. Join measured token/request/compute quantities to cost estimates.
3. Generate Pareto-frontier and SLO-budget tables.
4. Add sample reports clearly labeled as synthetic or environment-specific.
5. Update pattern guidance only with measured evidence and its environment context.

Acceptance:

- Fixed and variable costs remain separate.
- Unknown costs never silently become zero.
- Reports do not present one environment's numbers as universal Azure performance.

### Phase 7: Documentation and blog augmentation

Update or add documentation that explains:

1. Which pattern to choose and why.
2. Which Microsoft tool to use for development experiments, load testing, production tracing, Search diagnosis, quality evaluation, and optimization.
3. How to reproduce every published comparison.
4. Why Agent Optimizer follows architecture and rubric selection.
5. Which surfaces are GA versus preview as of the documentation's stated date.
6. Known measurement boundaries and unavailable telemetry.

Correct current ambiguities if still present:

- Distinguish classic index Search from Knowledge Base agentic retrieval.
- Replace `no LLM` with the accurate ownership boundary when Copilot Studio performs generation.
- Reconcile Pattern C `sub-second` claims with measured p95 evidence.
- Reconcile conflicting defaults across README, environment examples, and architecture docs.
- Label existing `~1-2 s` and `~10-14 s` values illustrative unless reproduced by a committed report.

Produce a follow-up blog outline titled approximately:

> Choosing the Right Microsoft Retrieval and Agent Pattern: Measured Trade-offs Across Copilot Studio, Foundry IQ, Prompt Agents, and Hosted Agents

Use this narrative:

1. Start with the least agentic pattern that satisfies the requirement.
2. Use native citations before creating a locator service.
3. Use classic Search before agentic retrieval when decomposition is unnecessary.
4. Prefer direct Foundry IQ before adding another prompt-agent layer when requirements allow it.
5. Use deterministic tools for deterministic tasks.
6. Choose managed versus hosted agents based on runtime control requirements.
7. Optimize the chosen eligible agent only after the dataset and rubric are trustworthy.

### Phase 8: React decision workbench

Implement this phase after Phase 1 has produced a stable normalized result and report. It may proceed alongside later backend phases by using synthetic fixtures, but it must not invent contracts for unfinished providers.

#### Step 8.1: Prove the custom UI gap

1. Configure or document Application Insights Agent details for the shared telemetry resource.
2. Create or document one saved Grafana dashboard covering the operational summary that Microsoft already supports.
3. Map each proposed workbench route to a user decision that the native experiences do not answer end to end.
4. Remove or replace screens that merely duplicate native views.
5. Write an architecture decision record covering React versus native Agent details/Grafana/Foundry views.

Acceptance:

- Every custom route has a documented decision question and authoritative data source.
- Native Microsoft views remain the drill-down destination.
- Current GA/preview status and verification date are recorded.

#### Step 8.2: Establish contracts and scaffold

1. Add versioned read-only BFF endpoints for capabilities, experiment lists, experiment detail, and comparison.
2. Generate TypeScript types from the normalized schema.
3. Scaffold the React app only after inspecting the target repo's package manager and frontend conventions.
4. Add the application shell, routing, error boundary, query client, theme, and synthetic fixture mode.
5. Add lint, type-check, unit-test, build, and Playwright commands without changing Python runtime dependencies.

Acceptance:

- The frontend runs entirely from synthetic/local artifacts with no Azure credentials.
- A schema change that breaks compatibility fails contract generation or tests.
- Production Azure APIs are not called from the browser.

#### Step 8.3: Deliver the read-only experiment vertical slice

1. Implement Experiments, Experiment detail, and Compare routes.
2. Show provenance, p50/p95/p99, quality, reliability, cost-estimate status, sample warnings, and unavailable-data reasons.
3. Add URL-addressable filters and baseline/candidate selection.
4. Add accessible tables and normalized JSON/CSV download.
5. Deep-link trace/evaluation fields only when providers expose an authorized source URL.

Acceptance:

- One fixture experiment can be listed, opened, and compared end to end.
- Relative deltas handle zero, null, unknown, and not-applicable values correctly.
- Keyboard, screen-reader labels, narrow viewport, and empty/error states are tested.

#### Step 8.4: Add pattern decisions, Pareto, and SLOs

1. Implement the A/A2/B/C/Hosted evidence matrix.
2. Implement threshold controls for quality, latency, reliability, security, and estimated cost.
3. Display qualifying configurations and the Pareto frontier with sample/confidence warnings.
4. Separate cold/warm, controlled/load/production, measured/estimated, and GA/preview comparisons.
5. Generate a shareable decision summary with manifest and report IDs.

Acceptance:

- The UI cannot compare incompatible result scopes without an explicit warning.
- Pareto membership is computed and tested in the backend domain layer, not inferred from chart pixels.
- The recommendation explains failed thresholds and never silently selects a winner.

#### Step 8.5: Add modular Microsoft providers

1. Implement `CapabilityProvider` first so unavailable integrations degrade cleanly.
2. Add read-only Application Insights summaries using allowlisted KQL and GenAI OTel conventions.
3. Add Foundry evaluation metadata/results only through current documented APIs.
4. Add Load Testing/Locust result import and Search operational summaries where supported.
5. Add estimated and actual-cost sources as separate series with separate freshness and scope labels.
6. Add authoritative deep links for all provider-owned detail.

Acceptance:

- Each provider can be disabled without breaking unrelated routes.
- Preview API removal produces a capability warning, not an application failure.
- Provider fixtures and errors contain no credentials, prompts, responses, or private document text.

#### Step 8.6: Secure, observe, and package

1. Add Entra authentication and explicit app authorization for deployed mode.
2. Add backend managed identity, least-privilege resource scopes, rate limits, and audit telemetry.
3. Add workbench OTel spans, frontend error reporting, provider latency, and cache metrics without sensitive content.
4. Add dependency/license review, accessibility testing, responsive Playwright screenshots, and bundle-size checks.
5. Document local artifact mode, connected Azure mode, configuration, provider updates, and schema migration.
6. Add deployment infrastructure only after explicit user approval and selection of an Azure hosting model.

Acceptance:

- Unauthorized and cross-environment access fails closed.
- No secrets or Azure management tokens appear in the built frontend bundle.
- The application remains useful when all optional Azure providers are disabled.
- Deployment is reproducible through the repo's chosen IaC and does not require portal-only configuration.

## Validation Requirements

Run, in order when available:

1. Focused unit tests after each edit slice.
2. Type checking and linting for touched modules.
3. Full mock/offline tests.
4. Opt-in live smoke tests only when credentials and explicit permission are available.
5. A tiny local Locust smoke run against a non-production target when a local server can be started safely.
6. Documentation link and example-command checks where the repo provides them.
7. Frontend formatting/linting, TypeScript checking, unit/component tests, and a production build.
8. Playwright verification at representative desktop and mobile viewports for the critical list-detail-compare-Pareto workflow.
9. Accessibility checks, nonblank chart checks, deep-link validation, and a scan of the built bundle for secrets or management tokens.
10. Provider contract tests for disabled, unauthorized, stale, partial, preview-removed, and schema-version mismatch states.

Never install packages globally. Use the repo's existing `uv` environment and dependency groups. Do not deploy Azure resources, run paid evaluation jobs, invoke Agent Optimizer, or run load against a remote endpoint without explicit user approval.

## Deliverables

Complete as much as the current environment can validate, prioritizing working code over broad scaffolding.

Required deliverables:

- Versioned experiment and result contracts.
- At least one complete adapter-to-report vertical slice.
- Contract tests and focused metric tests.
- A Microsoft asset reuse matrix in the docs.
- An implementation roadmap showing completed and deferred phases.
- Updated pattern guidance that distinguishes evidence from illustrative claims.
- A React workbench architecture decision record and native-versus-custom responsibility matrix.

When the environment permits, also deliver:

- All runnable pattern adapters.
- Locust tasks and Azure Load Testing instructions.
- Foundry evaluation integration.
- OTel correlation attributes and KQL.
- Cost/Pareto reports.
- Agent Optimizer extension/export documentation.
- Follow-up blog outline.
- Read-only React Benchmark and Decision Workbench with synthetic/local mode.
- Versioned BFF provider contracts, generated TypeScript types, and provider fixtures.
- Native Agent details, Grafana, Foundry, Search, Load Testing, and Cost Management deep links.

## Final Response

Report concisely:

- What was implemented and where.
- Which gaps are now addressed.
- Which Microsoft assets are reused directly versus adapted.
- Focused and full validation results.
- Live/paid validations not run.
- Remaining phases and why they remain.
- Any current Microsoft API or preview-status changes discovered during implementation.
- Which proposed UI capabilities were delegated to Microsoft-native experiences and which decision gaps justified custom React screens.

Do not claim completion for placeholder adapters, unexecuted paths, or unsupported telemetry.
