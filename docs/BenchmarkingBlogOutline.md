# Blog Outline: Choosing an HR Retrieval Architecture with Evidence

## Publication Gate

Do not publish comparative latency, quality, reliability, or cost conclusions
until the cited result artifacts are committed with their manifest, sample
count, environment, commit, corpus/index fingerprint, model deployment, and
measurement boundary. The existing `~1-2 s` and `~10-14 s` values are
illustrative labels, not findings.

## Audience and Thesis

- Audience: architects and engineering teams choosing among Copilot Studio,
  Azure AI Search, Foundry Agent Service, MCP, and hosted-agent paths.
- Thesis: architecture selection is a constrained evidence problem, not a
  latency leaderboard. A useful decision joins reproducibility, retrieval and
  answer quality, reliability, security boundaries, observability, and cost.

## Story

1. Define Patterns A, A2, B, C, and Hosted by automation, retrieval, generation,
   and telemetry ownership boundaries.
2. Explain why controlled experiments, capacity tests, and production telemetry
   are different evidence classes.
3. Show the normalized manifest, case, aggregate, load, cost, Pareto, and SLO
   contracts without exposing policy content.
4. Compare only compatible manifests and explain unavailable values rather than
   rendering them as zero.
5. Use deterministic citation, refusal, and locator checks as release gates;
   layer optional Foundry RAG evaluators over a reviewed gold set.
6. Show the React decision workbench as a read-only cross-product summary, then
   deep link to Agent details, Grafana, Foundry evaluations, Search diagnostics,
   Load Testing, and Cost Management for investigation.
7. Present connected results with confidence limits, failure counts, token
   context, and caveats. Discuss Pareto and SLO qualification before naming a
   preferred pattern.

## Required Evidence Figures

- Architecture boundary matrix with GA/Preview labels and verification date.
- Manifest compatibility and provenance screenshot.
- Quality-by-category table with deterministic and optional judge scores kept
  distinct.
- p50/p95/p99 latency chart annotated with sample count and wall-time boundary.
- Reliability and throttling view from bounded telemetry or load-test artifacts.
- Cost estimate with pricing-profile version and a link to Cost Management for
  billed cost.
- Pareto/SLO view with failed constraints visible.

## Claims Checklist

- Replace illustrative timing labels with measured values or remove them.
- Identify cold/warm state, concurrency, region, Search SKU/capacity, model,
  token counts, and output limits.
- State when Copilot-owned generation or unsupported invocation prevents direct
  instrumentation.
- Label the GA `2026-04-01` Knowledge Base surface separately from features
  requiring `2026-05-01-preview`.
- Label Application Insights Agent details and Foundry Agent Monitoring views
  as Preview while that remains true.
- Link every recommendation to a committed report and reproducible manifest.