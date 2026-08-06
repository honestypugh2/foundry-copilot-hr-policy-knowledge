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
- Every metric displays unit, sample count, source, freshness, and measurement
  type; unavailable values never render as zero.
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

The first release includes overview, experiment detail, comparison, pattern,
Pareto/SLO, capability, and provenance views. Native links are configured on
the server, restricted to HTTPS, and omitted when unavailable or invalid.

Local acceptance includes component tests plus Playwright desktop and mobile
workflows, axe accessibility checks, horizontal-overflow checks, nonblank
Pareto rendering, and a production Vite build. Vite defaults to port `5174`.
Connected Azure links and evidence remain unavailable until their providers are
configured and authorized.