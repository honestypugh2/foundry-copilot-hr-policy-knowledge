# Benchmark Workbench — the decision app

A local, read-only web app that turns committed benchmark artifacts into a
decision. It does not run experiments, does not call Azure, and does not store
results. It reads the JSON that the benchmark CLI already wrote under
`experiments/reports/` and renders it under the rules in
[BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md).

If you want the *rules*, read that document. This one explains what the app is
for, when to open it, and when to ignore it.

![Benchmark Workbench Overview page showing the architecture map, benchmark charts, hosted-mode quality, and evidence ledger](images/app/01-overview.png)

---

## Why it exists

Five retrieval patterns were measured at three different boundaries, in two
different cost units, by four different evaluation harnesses. That evidence is
correct and it is also unreadable as raw JSON. The failure mode is not missing
data. The failure mode is a reviewer opening two report files, seeing two p95
numbers, and ranking them — when those numbers were never comparable.

The workbench exists to make that specific mistake hard:

- It shows every metric **with the boundary it was measured at**, so a
  front-door number is never displayed as if it were a component number.
- It keeps the **two cost lanes separate**. Copilot Credits and Azure per-token
  USD never appear in the same total.
- It renders missing evidence as **unavailable, not zero**. A `null` cost on a
  Copilot Studio run is a correct answer, not a gap to be filled with 0.
- It **refuses to produce a recommendation** when the gates are not met.

![Explanation of the decision gaps the benchmark workbench fills across Microsoft-native tools](images/app/overview/07-why-this-workbench-exists.png)

## When to use it, and when not to

The workbench leads during design and release qualification. Microsoft-native
tools lead in production. It deep-links out to them rather than imitating them.

| Phase | Use | Why |
| --- | --- | --- |
| Design / pattern selection | **Workbench** | Cross-product comparison is the whole question, and no native tool spans Copilot Studio and Foundry. |
| Release qualification | **Workbench** | Gates, confidence intervals, and fail-closed comparison live here. |
| Production monitoring | **Azure Monitor, Application Insights, Foundry monitoring** | They own live telemetry; the workbench holds no runtime state. |
| Root-cause on one trace | **Foundry tracing / App Insights** | The workbench links out; it is not a trace explorer. |
| Billed-cost reconciliation | **Azure Cost Management, Power Platform admin center** | Those are authoritative for money. The workbench only estimates. |

![Integration model showing when the benchmark leads and when Microsoft-native services lead across the lifecycle](images/app/overview/08-integration-model.png)

Do **not** use it to:

- discover new results (it only reads what you already committed),
- compare runs whose scope fields differ (it will refuse; see below),
- quote billed cost (it estimates; the admin surfaces are authoritative).

## What each view answers

| View | Question it answers |
| --- | --- |
| **Overview** | Which patterns exist, which have evidence, and what does the evidence say at a glance? |
| **Experiments** | What has actually been run, at which boundary, on which dataset version? |
| **Experiment detail** | For one run: latency percentiles, reliability, quality, security, cost, and full provenance. |
| **Compare** | Are these two runs even comparable, and if so, how do they differ? |
| **Pareto / SLO** | Which runs clear the release gates, and which are blocked and why? |
| **Evidence coverage** | Which decision evidence lives here versus in an authoritative Microsoft-native system? |
| **Glossary** | What do measurement boundary, evidence class, and cost lane mean here? |

### The two views that carry the argument

**Compare fails closed.** If two runs differ on dataset, corpus fingerprint,
index fingerprint, answer model, or measurement boundary, the app declines to
rank them and names the mismatch. This is the guardrail that stops a
five-pattern leaderboard from being assembled by accident.

![Compare view that fails closed when two runs have incompatible dataset, corpus, index, model, or measurement boundary](images/app/04-compare.png)

**Pareto / SLO shows the blockers, not just the winners.** Gate thresholds are
stated, and runs that miss them are labeled exploratory rather than quietly
dropped.

![Pareto and SLO qualification view listing gate thresholds and which runs pass or are blocked](images/app/05-pareto-slo.png)

### Cost, shown as two lanes

The Copilot Studio lane is denominated in **Copilot Credits**, rated per agent
activity, and is estimated from each agent's configuration against a committed
rate card. The Foundry lane is **per-token USD**, priced from service-reported
token counts against a dated pricing profile. The app never adds them.

![Benchmark summary charts: response time by pattern, quality and security gates, and the two separate cost lanes for Copilot Credits and Foundry per-token cost](images/app/overview/03-benchmark-at-a-glance.png)

## Run it

The launcher starts the FastAPI backend on `:8000` and the Vite frontend on
`:5174`, with Azure calls disabled so it reads only committed artifacts.

```bash
scripts/app.sh start     # then open http://127.0.0.1:5174
scripts/app.sh status
scripts/app.sh logs
scripts/app.sh stop
```

`restart` is also available. No Azure credentials and no spend are required:
the backend runs with `USE_AZURE_SERVICES=false` and reads
`experiments/reports/`.

## What it reads

Nothing in the app is authored by hand. Every number originates in a committed
artifact:

| Input | Path |
| --- | --- |
| Run manifests | `experiments/manifests/` |
| Per-case results, aggregates, evaluations | `experiments/reports/` |
| Azure per-token rates | `experiments/pricing/azure-*.json` |
| Copilot Credit rate card and feature mix | `experiments/pricing/copilot-studio-credits-*.json` |

The published evidence bundle is
[`decision-system-20260811`](../experiments/reports/decision-system-20260811),
pinned to a clean commit. If a number is not traceable to a manifest and a
report, the app does not display it.

## Screenshots and alt text

Every screenshot, with the alt text to reuse when embedding it, is indexed in
[docs/images/app/README.md](images/app/README.md). That index also records the
capture provenance, which matters because the images are evidence about the app,
not decoration.

## Related documents

| Document | Scope |
| --- | --- |
| [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md) | The rules the app enforces: boundaries, evidence classes, gates, cost lanes. |
| [ReactBenchmarkWorkbenchADR.md](ReactBenchmarkWorkbenchADR.md) | Why the app is read-only, and which responsibilities stay with Microsoft-native tools. |
| [PatternSetupAndBenchmarkGuide.md](PatternSetupAndBenchmarkGuide.md) | How to produce the runs the app reads. |
| [CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md) | Front-door measurement over Direct Line and the Copilot Credits lane. |
| [ReuseForYourUseCase.md](ReuseForYourUseCase.md) | Point the same workbench at a different corpus and use case. |
