# Benchmarking Retrieval Patterns for Copilot Studio and Foundry IQ: An Evidence System, Not a Leaderboard

*Part 2 of a series. Part 1, [Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337), showed five ways to ground an agent. This part is about how to choose between them with evidence you can defend.*

![Benchmarking retrieval patterns for Copilot Studio and Foundry IQ — an evidence system, not a leaderboard. Part 2 of the series, summarizing three rules (measure the boundary, separate the cost lanes, gate on deterministic checks) across five patterns; front doors run Claude Sonnet 4.6 and backends synthesize on gpt-5-mini.](../images/banner-part2.png)

> **Reference implementation, not a production template.** The sample and numbers below are for learning and experimentation. Before you ship, review the [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/) for reliability, security, cost, and operations guidance.

---

## The wrong first question

Part 1 gave you five ways to ground a Microsoft Copilot Studio agent in HR policy content: connect Copilot Studio straight to an Azure AI Search index (Pattern A), reach a Foundry IQ knowledge base through Microsoft IQ for agentic retrieval (Pattern A2), wrap the knowledge base in a Microsoft Foundry Agent Service prompt agent (Pattern B), route locator questions to a deterministic REST endpoint (Pattern C), or run the loop yourself in a Microsoft Agent Framework container (Hosted).

![One Copilot Studio front door routes to five grounded-agent patterns: A (Azure AI Search), A2 (Foundry IQ agentic knowledge base), B (Foundry Agent Service), C (deterministic locator), and a self-hosted Agent Framework runtime.](../images/app/overview/architecture-map.gif)

The obvious next question is "which one is fastest?" It is also the wrong first question.

Here is why. Drop a p95 latency chart of all five patterns on a slide and someone will pick a winner in ten seconds. But that chart almost always compares numbers that were never comparable: some were measured through the Copilot Studio front door (including a Direct Line network hop), others at the deployed agent boundary; one path runs a model on every turn while another returns a document link with no model at all; one is billed in per-message Copilot Studio Credits and another in per-token Azure charges. The chart *looks* like a decision. It is a category error with axis labels.

This post is about the alternative: a small, reproducible **evidence system** that makes an architecture choice you can explain to a skeptical reviewer. Three rules, one normalized contract, a set of release gates, and a worked example you can run yourself. By the end you will know exactly which claims your data supports — and which ones it does not yet.

## Three classes of evidence that do not mix

The first discipline is to stop treating three different kinds of measurement as one.

| Evidence class | What it is | What it answers | What it must never do |
| --- | --- | --- | --- |
| **Controlled experiment** | Sequential cases run against a recorded manifest | "Which pattern/config is better, all else equal?" | Be blended with concurrent load rows |
| **Load / capacity test** | Concurrent traffic with a named profile and saturation signals | "How does it behave under N users?" | Be merged into sequential latency percentiles |
| **Production telemetry** | Observed user traffic in Application Insights, Foundry, Azure AI Search, and Azure Monitor | "What is actually happening in production?" | Be reconstructed into controlled percentiles |

![Three classes of evidence that do not mix: controlled experiments (which config is better, all else equal), load or capacity tests (behavior under N concurrent users), and production telemetry (what is actually happening in production) — each answers a different question and is never blended with the others.](diagrams/three-evidence-classes.png)

A latency value is only "measured" when a committed result records its manifest, sample count, environment, and measurement boundary. Anything else — including the friendly `~1–2 s` and `~10–14 s` labels from Part 1 — is an illustration, not a finding. Keeping these classes separate is not bureaucratic; it is what stops a load-test spike from masquerading as a typical response time.

## Rule 1: Measure the boundary you actually ship

Every pattern is timed at an explicit **measurement boundary**, and the boundaries are not interchangeable.

- **A, A2, and C** are measured through the **Copilot Studio front door** over Direct Line. The timer wraps one opaque span: send the question, await the final activity, stop. Everything Copilot Studio does inside — generative answer, knowledge call, REST tool, connected agent — is Microsoft-managed and not individually timed. All five front doors pin the same answer model, **Claude Sonnet 4.6**, so the front-door lanes differ only by harness and retrieval path, not model.
- **B and Hosted** are also measured at their **deployed-agent boundary** — where the answer is synthesized on `gpt-5-mini` — because native evaluation cannot grade the external-agent hop from the outside.

That leads to the single most important rule in the whole system:

> Never subtract one boundary from another and call the difference "Copilot Studio overhead." Different boundaries are different experiments.

In production, B and Hosted still sit behind the front door too, so the user-facing latency is roughly the deployed p50 plus the same front-door overhead the A/C paths pay. We say that in words; we do not fabricate it with subtraction.

![Measurement boundaries: patterns A, A2, and C are timed at the Copilot Studio front-door boundary over Direct Line — the timer wraps the opaque orchestration (generative answer on Claude Sonnet 4.6, knowledge call, REST tool, connected-agent call); patterns B and Hosted are timed at the deployed-agent boundary where the answer is synthesized on gpt-5-mini. Never subtract one boundary from another.](diagrams/measurement-boundaries.png)

The adapter records `client_wall_time_ms` as `measured` and `service_elapsed_time_ms` as `unavailable` with reason `NOT_EXPOSED`. Missing is recorded as missing — never as zero.

## Rule 2: Two cost lanes that never add up

Cost is where leaderboards quietly lie, because the patterns are not billed in the same unit.

| Lane | Patterns | Unit | Source |
| --- | --- | --- | --- |
| **Azure per-token USD** | B, Hosted (local, token-instrumented) | USD per invocation from service-reported input/cached/output tokens × a dated retail pricing profile | SDK final usage × pricing profile |
| **Copilot Studio (Credits / messages)** | A, A2, C, and the B/Hosted front doors | Per-message Copilot Studio billing — standard-harness messages (A, C, B/Hosted) and GitHub Copilot-harness Credits (A2) | Copilot Studio → Operate → Cost / Power Platform admin center |

A `null` per-token cost on a Copilot Studio front-door run is **correct, not missing** — that lane is not token-metered, so it can never join the per-token axis. We estimate each lane on its own meter and reconcile against the authoritative source (Azure Cost Management for tokens; the Power Platform admin center for Credits), and we never sum a Credit and a token. For Pattern B and the Hosted front door, the connected Foundry model's tokens are billed on the Azure lane *in addition* to Copilot Studio Credits — two lanes, stated separately.

One more reason the Credits lane can't be token-priced: in Copilot Studio the **harness** is the runtime and the **model** is a separate selectable engine. Patterns A, C, and the B/Hosted front doors run on the **standard harness**; Pattern A2 runs on the **GitHub Copilot harness**. The model is now selectable and disclosed — this project pins **Claude Sonnet 4.6** on all five front doors for parity — so we record `answer_model` as `<harness>:<model>` (`microsoft_managed_standard_harness:claude-sonnet-4.6` or `github_copilot_harness:claude-sonnet-4.6`). It still can't join the per-token axis: the standard harness bills as per-message Copilot Studio messages and the GitHub Copilot harness bills in Copilot Credits — two Copilot Studio meters, neither token-metered. We compare quality *within* a platform first, because the harness (and any model change) is a confound across them.

## Rule 3: Deterministic gates first, model judges second

Quality is graded in two tiers, and the order matters.

1. **Deterministic graders** are the release gates: does the answer cite the expected policy IDs, refuse when it should, and — for locator queries — return the exact source URL? These are code, not opinions, so they are reproducible and auditable.
2. **Model-based judges** (relevance, groundedness, task adherence via the Foundry evaluators) are **supplemental**. They are calibrated against a small reviewed gold set and reported next to — never on top of — the deterministic results.

```python
# Deterministic citation gate (illustrative)
def citation_pass(answer_text: str, expected_policy_ids: list[str]) -> bool:
    return all(pid in answer_text for pid in expected_policy_ids)
```

When a judge disagrees with the gold set, the gold set wins. That single rule keeps a chatty model from grading its own homework.

## One contract to make runs comparable

The three rules are enforced by a normalized contract: `ExperimentManifest`, `CaseResult`, and `AggregateReport`, all strict, versioned (`schema 1.0`) Pydantic models. The manifest carries the provenance that makes a comparison legitimate:

```jsonc
{
  "schema_version": "1.0",
  "dataset_version": "copilot-hr-policy-release-v2",
  "corpus_fingerprint": "<sha>",
  "index_fingerprint": "<sha>",
  "model_deployment": "gpt-5-mini:2025-08-07",
  "pricing_profile": "azure-gpt-5-mini-global-standard-cache-aware:2025-08-01",
  "measurement_boundary_class": "copilot_studio_direct_line",
  "warmups": 3,
  "repetitions": 35
}
```

The comparison surface **fails closed**: if two runs differ in dataset, corpus, index, model, retrieval mode, or measurement boundary, the tool refuses to rank them instead of drawing a tidy, misleading bar chart. Retrieval references keep stable source IDs and omit policy content by default, so nothing sensitive lands in an artifact.

![Compare view that refuses to rank two runs when their dataset, corpus, index, model, or measurement boundary differ.](../images/app/04-compare.png)

Running it is a two-line CLI. The offline smoke validates the contract with fixtures and no Azure spend:

```bash
python -m src.benchmarking.cli \
  --manifest experiments/manifests/synthetic-direct-search.json \
  --cases experiments/datasets/synthetic-migration-smoke.json \
  --fixture-responses experiments/datasets/synthetic-direct-search-responses.json \
  --output-dir experiments/reports/synthetic-direct-search
```

Fixture wall-times are contract checks, not Azure performance evidence — and the reports label them that way.

## A worked example: three ways to retrieve, measured

Here is the part where most posts would hand you a five-pattern leaderboard. This one gives you one lane where every number is token-metered and every retrieval type shows up — the Hosted runtime's three retrieval modes — and then tells you exactly where the other four patterns' evidence sits and why you cannot stack it into the same bar chart.

The Hosted runtime supports three retrieval modes. All three ran over the same synthetic HR corpus and the same versioned release set, 35 timed invocations each with declared warmups, on `gpt-5-mini` priced by the `azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` profile. Deterministic quality is graded on the release set's seven quality cases; security passed on both security cases for every mode.

| Hosted retrieval mode | Retrieval type | Deterministic quality (7-case set) | p95 latency (35 runs) | Est. model cost / answer |
| --- | --- | ---: | ---: | ---: |
| `tool` (custom `@tool` hybrid search) | Classic search | 100% (7/7) | ~25.8 s | ~USD 0.0033 |
| `context-semantic` (built-in context provider) | Classic search | 71.4% (5/7) | ~38.2 s | ~USD 0.0031 |
| `context-agentic` (context provider over the Foundry IQ knowledge base) | Agentic retrieval | 100% (7/7) | ~34.7 s | ~USD 0.0032 |

Two honest caveats travel with that table. First, quality is graded on a seven-case set: `context-semantic` misses two of seven, while `tool` and `context-agentic` pass all seven — a seven-case gate is not a mature quality benchmark, so expand the dataset before reading too much into that gap. Second, with only 35 samples a single slow request moves p99 materially (tool's p95 is about 25.8 s), so every percentile is reported with its sample count and a small-sample warning. Numbers without their error bars are decoration.

> **Provenance.** These figures come from the committed publication bundle (`decision-system-20260811`, clean commit `9c94215`) — 35 timed invocations per mode with declared warmups, priced against the `azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` profile. The report artifacts live under `experiments/reports/decision-system-20260811/hosted/`; if you cannot point a number back to a committed manifest and report, it does not belong in the post.

The same bundle measures the other four patterns too — but at different boundaries, which is exactly why Rule 1 keeps them off the chart above. Patterns A, A2, and C were run through the Copilot Studio front door over Direct Line (native-evaluation quality of 85.7%, 85.7%, and 71.4% on the seven-case set — all three front doors pinned to the same model, **Claude Sonnet 4.6**, so the remaining difference is the harness: A and C on the standard harness, A2 on the GitHub Copilot harness); Pattern B and the deployed Hosted runtime were measured at the deployed-agent boundary on `gpt-5-mini` (71.4% each), because native front-door evaluation returns an error across the external-agent hop. Where a lane is genuinely incomplete — front-door A2 latency, isolated load, billed-cost reconciliation — the workbench shows it as unavailable, not zero.

## Release gates, not vibes

A run becomes a *recommendation* only when it clears an explicit gate profile. These are project acceptance criteria for this reference assistant — not Microsoft service guarantees — and you should set your own with your product and operations owners:

| Gate | Threshold (this reference project) |
| --- | ---: |
| Deterministic quality | ≥ 85% |
| Copilot Studio client p95 | ≤ 30 s |
| Success rate | ≥ 99% |
| Security pass rate (prompt-injection, secret-disclosure) | 100% |
| Estimated variable model cost | ≤ USD 0.05 / request |

The workbench produces **no recommendation** when front-door evidence, category-level quality, confidence intervals, explicit outcome counts, security results, or variable-cost evidence is missing. A Pareto-optimal point without those gates is labeled exploratory, not a release call. That is the publication gate in software form: the system would rather say "not yet" than ship a confident wrong answer.

![Pareto and SLO qualification view listing gate thresholds and which runs pass or are blocked.](../images/app/05-pareto-slo.png)

## Reuse the native tools; do not rebuild them

The evidence system is an augmentation layer, not a replacement for Microsoft-native observability. Application Insights and Azure Managed Grafana own production traces, dashboards, and alerts; Microsoft Foundry owns agent monitoring and cloud evaluation; Azure AI Search owns retrieval capacity and throttling (its agentic retrieval REST surface is **GA at `2026-04-01`**); Azure Load Testing owns concurrent-load evidence; and Azure Cost Management owns billed cost. Agent-level views in Application Insights and Foundry's agent monitoring dashboards are **preview** as of writing.

The workbench normalizes just enough to make a cross-product decision, then deep-links out to those systems for root-cause work. It does not copy their detail views or pretend to be a trace explorer.

## What this does not claim (yet)

Being explicit about gaps is what makes the rest credible:

- Category-level quality, confidence intervals, and explicit failure counts are not yet in the aggregate contract.
- Connected production and isolated load evidence is pending.
- Billed-cost reconciliation against Azure Cost Management is pending by design — shared resources are not attributed per request without a declared allocation rule.

None of these are fudged into the charts. Missing stays missing.

## Try it yourself

You have a few ways to go deeper, depending on where you are:

1. **Start with the architecture.** If you have not read Part 1, [Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337) defines the five patterns this post benchmarks.
2. **Run the offline contract smoke** (no Azure spend) to see the normalized manifest, case, and aggregate reports on your own machine.
3. **Benchmark your own agents.** Stand up five non-production Copilot Studio agents — one per pattern — and run the Direct Line harness so each measurement exposes exactly one retrieval path.
4. **Go deeper on the method** in Microsoft Learn: [Azure AI Search agentic retrieval](https://learn.microsoft.com/azure/search/search-agentic-retrieval-concept), [Foundry IQ](https://learn.microsoft.com/azure/ai-foundry/), and [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/).

Then tell me in the comments: when you choose a retrieval architecture, which evidence class do you trust most — a controlled run, a load test, or production telemetry? That answer usually reveals which mistake you are most likely to make next.

*Ask HR is a development and learning sample. Production deployments should add authentication, monitoring, data governance, content safety, and compliance controls appropriate to your organization.*
