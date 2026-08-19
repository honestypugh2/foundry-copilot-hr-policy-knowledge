# ADR: React Benchmark Workbench Boundary

- **Status:** Implemented
- **Date:** 2026-08-03
- **Decision:** Use a thin, read-only React decision plane over versioned,
  generated backend contracts. Keep Microsoft-native products as the
  operational plane.

## Context

Application Insights Agent details (Preview), Grafana dashboards, Foundry
monitoring/evaluation, Azure AI Search monitoring, Load Testing, and Cost
Management already provide authoritative product-specific investigation. They
do not jointly answer whether A, A2, B, C, or Hosted satisfies one HR workload's
quality, latency, reliability, security, and cost thresholds under comparable
manifests.

## Decision

The workbench will summarize normalized evidence, compare compatible
experiments, evaluate SLOs and Pareto trade-offs, expose provenance, and deep
link to authoritative Microsoft views. It will not execute deployments, load
tests, optimization, or production mutations in its first release. Azure
credentials and SDK calls remain server-side behind versioned, read-only
provider contracts.

| Route or responsibility | Decision question | Owner |
| --- | --- | --- |
| Overview | Is evidence fresh, available, and meeting selected SLOs? | **Custom summary**, with native deep links. |
| Experiments | Which patterns used the same dataset, corpus/index, commit, and environment? | **Custom** normalized manifest table. |
| Experiment detail | What was measured, estimated, unavailable, and why? | **Custom** evidence view; native reports own detailed evaluation/trace data. |
| Compare | What changed between compatible baseline and candidate manifests? | **Custom** absolute/relative deltas and warnings. |
| Patterns | Which automation, generation, and telemetry boundaries apply to A/A2/B/C/Hosted? | **Custom** evidence matrix. |
| Pareto and SLO | Which configurations qualify without ranking latency alone? | **Custom** tested domain calculation and accessible presentation. |
| Operations | Where is the production issue and where should investigation continue? | **Native** Agent details, Grafana, Foundry, Search, and Load Testing; custom summary only. |
| Data and provenance | Can this comparison be reproduced? | **Custom** versions/fingerprints; native resources remain authoritative. |
| Trace waterfall and transaction search | What happened in one invocation? | **Native Application Insights Agent details**. |
| Operational charts, alerts, and KQL exploration | Is production behavior changing? | **Native Grafana/Azure Monitor**. |
| Evaluation drill-down and continuous evaluation | Why did quality change? | **Native Foundry evaluation**. |
| Search service capacity | Are replicas, partitions, throttling, or ingestion limiting service? | **Native Azure AI Search/Azure Monitor**. |
| Actual billing analysis | What did Azure bill? | **Native Azure Cost Management**. |

## Consequences

- The React application consumes generated/shared schema types and is not a
  second schema authority.
- Experiment views display metric units plus run-level sample/configuration
  context; unavailable values never render as zero.
- Provider capability states include unavailable, not configured, not
  authorized, not applicable, degraded, and preview status.
- Filters and comparisons are URL-addressable, while credentials, prompts,
  responses, and policy content are excluded from browser storage.
- Detailed native links are shown only when an authorized provider supplies an
  allowlisted URL.

## Implemented Boundary

The implementation gate is satisfied by the strict artifact-backed BFF,
canonical JSON Schema export, generated TypeScript transport contracts, and
compatible synthetic fixtures. The frontend normalizes transport data into
provider view models without becoming a second schema authority.

The first release includes an architecture decision overview plus experiment
detail, comparison, pattern, Pareto/SLO, evidence-coverage, and Operations
views. Provenance remains contextual in experiment detail, while the complete
capability registry stays available through the read-only API instead of a
standalone frontend inventory. The overview joins measured retrieval modes,
all A/A2/B/C/Hosted paths, evidence gaps, and authoritative-system ownership
without copying native product detail. Native links are configured on the
server, restricted to HTTPS, and omitted when unavailable or invalid.

Local acceptance includes component tests plus Playwright desktop and mobile
workflows, axe accessibility checks, horizontal-overflow checks, nonblank
Pareto rendering, and a production Vite build. Vite defaults to port `5174`.
Connected Azure links and evidence remain unavailable until their providers are
configured and authorized.
## Amendment: route map as shipped (2026-08-19)

This ADR is a historical record and its decisions stand. Two route names in the
table above did not survive contact with the implementation, so the mapping is
recorded here rather than edited in place:

| ADR row | Where it shipped |
| --- | --- |
| Patterns | Folded into **Overview** as the architecture-paths panel; there is no `/patterns` route. |
| Operations | Folded into **Evidence coverage** (`/coverage`), which carries the custom-versus-native ownership matrix. |

Shipped routes: `/`, `/experiments`, `/experiments/:id`, `/compare`, `/pareto`,
`/coverage`, `/glossary`, plus `/knowledge-base` and `/about`.

For what the app is for and when to use it, see
[BenchmarkWorkbench.md](BenchmarkWorkbench.md). For the measurement rules it
enforces, see [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md).
