# Benchmark Workbench — App Screenshot Index

Screenshots of the **Benchmark Workbench** (the React decision surface served by
`scripts/app.sh`, code in [`src/frontend`](../../../src/frontend) and
[`src/benchmarking/api`](../../../src/benchmarking/api)). Each entry lists the
file, a one-line description, and the **alt text** to reuse when embedding the
image (the Foundry TechCommunity blog process requires alt text on every image).

## Capture provenance (read before reusing)

- **Build:** current `main` UI — "Pattern Lab / Architecture intelligence", dark
  theme, nav = Overview · Experiments · Compare · Pareto/SLO · Evidence coverage
  · Glossary.
- **Captured:** 2026-08-19, headless Chromium at 1600×1000 (section crops
  1312 px wide), backend in offline mode (`USE_AZURE_SERVICES=false`) reading
  committed artifacts under `experiments/reports/`. This capture reflects the
  Copilot Credits terminology sweep (the Copilot Studio cost lane now reads
  "Credits per interaction", rated per agent activity) and includes the
  `copilot-front-door-hosted-45-20260818` run in the Experiments ledger.
- **Authoritative numbers vs. these screenshots.** For *published* metrics, cite
  the committed publication bundle
  [`experiments/reports/decision-system-20260811`](../../../experiments/reports/decision-system-20260811)
  (commit `9c94215`) and its pinned figures in
  [`decision-system-20260811/figures/`](../../../experiments/reports/decision-system-20260811/figures).
  The Overview "Hosted retrieval" panel is pinned to the token-priced local
  Agent Framework lane and matches that bundle — **tool 100% (7/7),
  context-semantic 71.4% (5/7), context-agentic 100% (7/7)**, security 100%
  across all three (see
  [`decision-system-20260811/hosted/`](../../../experiments/reports/decision-system-20260811/hosted)).
  The Experiments ledger still lists every run across `experiments/reports/`.

## Tab views — [`docs/images/app/`](.)

| File | Shows | Alt text |
| --- | --- | --- |
| [`01-overview.png`](01-overview.png) | Full Overview page (long). Prefer the per-section crops below. | Benchmark Workbench Overview page showing the architecture map, benchmark charts, hosted-mode quality, and evidence ledger. |
| [`02-experiments-latency.png`](02-experiments-latency.png) | Experiments ledger: p95-by-run bar chart across every committed run, coloured by pattern, with the 30 s SLO line. | Bar chart of p95 latency for each committed benchmark run, coloured by pattern, with a 30-second SLO reference line. |
| [`03-experiment-detail.png`](03-experiment-detail.png) | One run's report: latency percentiles, reliability, quality/security, cost, provenance. | Experiment detail report for a single run showing latency percentiles, reliability, quality, security, cost, and provenance. |
| [`04-compare.png`](04-compare.png) | Compare view — refuses to rank runs whose scope fields differ (fails closed). | Compare view that fails closed when two runs have incompatible dataset, corpus, index, model, or measurement boundary. |
| [`05-pareto-slo.png`](05-pareto-slo.png) | Pareto / SLO qualification with failed constraints visible. | Pareto and SLO qualification view listing gate thresholds and which runs pass or are blocked. |
| [`06-evidence-coverage.png`](06-evidence-coverage.png) | Evidence coverage — what stays in the workbench vs. authoritative Microsoft-native systems. | Evidence coverage matrix mapping decision evidence in the workbench to the authoritative Microsoft-native systems. |
| [`07-glossary.png`](07-glossary.png) | Glossary of measurement-boundary, evidence-class, and cost-lane terms. | Glossary defining measurement boundary, evidence classes, and cost lanes used across the workbench. |

## Overview sections — [`docs/images/app/overview/`](overview)

| File | Shows | Alt text |
| --- | --- | --- |
| [`overview/architecture-map.gif`](overview/architecture-map.gif) ⭐ | Animated architecture map (**dark theme**), captured from the app's real click interaction — the active pattern lights up, the dashed connector line animates from the Copilot Studio front door, and the detail card below updates for each pattern (A → A2 → B → C → H). | Animated diagram: employees enter through Copilot Studio, which routes to five grounded-agent patterns — A (Azure AI Search), A2 (Foundry IQ agentic knowledge base), B (Foundry Agent Service), C (deterministic locator), and a self-hosted Agent Framework runtime; the selected pattern and its detail card update in turn. |
| [`overview/architecture-map-light.gif`](overview/architecture-map-light.gif) | Same animation in **light theme** (app theme toggle). | Animated diagram (light theme): Copilot Studio routing to five grounded-agent patterns A, A2, B, C, and Hosted, with the selected pattern and its detail card updating in turn. |
| [`overview/02-architecture-map.png`](overview/02-architecture-map.png) ⭐ | Static architecture map (same as the GIF, one frame). | Diagram of one Copilot Studio front door routing to five grounded-agent retrieval patterns A, A2, B, C, and Hosted. |
| [`overview/03-benchmark-at-a-glance.png`](overview/03-benchmark-at-a-glance.png) ⭐ | Latency, quality/security gates, and the two cost lanes (Copilot Credits vs Foundry per-token USD). | Benchmark summary charts: response time by pattern, quality and security gates, and the two separate cost lanes for Copilot Credits and Foundry per-token cost. |
| [`overview/09-hosted-retrieval.png`](overview/09-hosted-retrieval.png) | Hosted retrieval modes — tool 100% / semantic 71.4% / agentic 100% (35 cases each), pinned to `decision-system-20260811/hosted/`. | Panel comparing the three Hosted retrieval modes — tool retrieval 100%, semantic context 71.4%, and agentic context 100% deterministic quality, 35 cases each. |
| [`overview/10-architecture-paths.png`](overview/10-architecture-paths.png) | Pattern cards showing implementation state and evidence state as distinct signals. | Cards for patterns A, A2, B, C, and Hosted showing implementation status and benchmark-evidence status separately. |
| [`overview/11-evidence-ledger.png`](overview/11-evidence-ledger.png) | Recent-runs table (pattern × mode × dataset × boundary). | Table of recent benchmark runs listing pattern, retrieval mode, dataset version, and measurement boundary. |
| [`overview/01-benchmark-decision-system.png`](overview/01-benchmark-decision-system.png) | Page header + run-count summary. | Overview header stating the benchmark decision system and how many patterns have measured evidence. |
| [`overview/04-path-stats.png`](overview/04-path-stats.png) | Architecture-path stat cards. | Summary stat cards for the five architecture paths. |
| [`overview/05-decision-status.png`](overview/05-decision-status.png) | Decision-status ribbon. | Decision-status ribbon summarizing current qualification state. |
| [`overview/06-start-here.png`](overview/06-start-here.png) | "What this is and how to move around it" navigation guide. | Navigation guide explaining what the workbench is and how to move between its views. |
| [`overview/07-why-this-workbench-exists.png`](overview/07-why-this-workbench-exists.png) | Why the workbench exists — decision gaps it fills. | Explanation of the decision gaps the benchmark workbench fills across Microsoft-native tools. |
| [`overview/08-integration-model.png`](overview/08-integration-model.png) | When to use the benchmark vs. stay native (design → release → production → improve). | Integration model showing when the benchmark leads and when Microsoft-native services lead across the lifecycle. |
| [`overview/12-reuse-footer.png`](overview/12-reuse-footer.png) | "Fork this workbench" reuse footer. | Footer inviting readers to fork the workbench and drive it with their own normalized JSON contracts. |

## Regenerating these images

Screenshots and GIFs are captured with headless Chromium (Playwright, already
installed under `src/frontend/node_modules`) against a running workbench, then
GIFs are assembled with Pillow (no ffmpeg needed).

```bash
scripts/app.sh start                                   # backend :8000 + frontend :5174

# Architecture-map GIFs — real click interaction, dark + light themes:
cd src/frontend && node scripts/capture-architecture-gif.mjs   # writes frames to /tmp/archmap_{dark,light}
cd -
python scripts/assemble_gif.py /tmp/archmap_dark  docs/images/app/overview/architecture-map.gif
python scripts/assemble_gif.py /tmp/archmap_light docs/images/app/overview/architecture-map-light.gif
```

Still tab/section screenshots are captured by
`src/frontend/scripts/capture-app-screenshots.mjs` (tab views + Overview section
crops that clip each eyebrow-titled block):

```bash
cd src/frontend && node scripts/capture-app-screenshots.mjs
```

The pinned publication figures are produced by the benchmark reporting pipeline,
not by ad-hoc capture; treat `decision-system-20260811/figures/` as the
authoritative rendered evidence for that commit.
