---
name: continue-hr-policy-benchmark-migration
description: "Add the local latency and evaluation migration requirements to an HR policy benchmark implementation that is already running, without restarting completed work."
disable-model-invocation: true
---
# Continue the Existing HR Policy Benchmark Implementation

This is a follow-up instruction for work already in progress in the current clone of `honestypugh2/foundry-copilot-hr-policy-knowledge`.

Continue from the current implementation state. Inspect the current branch, working tree, completed edits, tests, and any implementation notes before making changes. Preserve all valid completed work. Do not restart the original prompt, discard working code, or repeat repository-wide exploration.

## Required Local Migration Audit

Before continuing the benchmark domain implementation, read the following migration-source files directly from the local checkout without modifying that repository:

```text
/home/brittanypugh/foundry-copilot-search-validate/src/latency/
/home/brittanypugh/foundry-copilot-search-validate/scripts/investigate_latency.py
/home/brittanypugh/foundry-copilot-search-validate/tests/test_latency_investigation.py
/home/brittanypugh/foundry-copilot-search-validate/evals/dataset.py
/home/brittanypugh/foundry-copilot-search-validate/evals/metrics.py
/home/brittanypugh/foundry-copilot-search-validate/evals/run_eval.py
/home/brittanypugh/foundry-copilot-search-validate/docs/CostComparison.md
/home/brittanypugh/foundry-copilot-search-validate/docs/RetrievalPatterns.md
```

Treat that checkout as migration evidence and test material only. Do not add a package, runtime, Git submodule, CI, or deployment dependency on it.

## Required Target Artifacts

Port the useful capabilities, not the source directory tree. Inspect the target repository's current package layout and extend its existing ownership boundaries. The completed target repository must contain equivalents of these artifacts:

1. A benchmark/experiment domain package containing normalized result models, activity records, stage timings, statistics, aggregation, and JSON/Markdown report serialization. Prefer the target's existing `src/evaluation/`, `src/benchmarking/`, or `src/experiments/` boundary. Create `src/latency/` only when latency is already an independent target-domain concern.
2. A benchmark runner or CLI replacing the useful behavior of `scripts/investigate_latency.py`, implemented against normalized pattern adapters rather than the old orchestrator.
3. Offline unit tests adapted from `tests/test_latency_investigation.py` for activity parsing, deterministic percentiles, cold/warm aggregation, error accounting, serialization, and fake adapters.
4. Evaluation dataset and metric modules integrated with the target's existing evaluation implementation, preserving the useful eight-category taxonomy, recall@k, MRR, citation, refusal, and optional faithfulness concepts.
5. Versioned experiment manifests plus normalized JSONL and Markdown outputs under the target's `experiments/` structure.
6. Target-owned documentation for measurement definitions, cost formulas and pricing profiles, migration decisions, and pattern interpretation.

Do not copy `src/latency/`, `evals/`, `scripts/investigate_latency.py`, or their imports wholesale. Adapt behavior and tests to the target's normalized contracts and current APIs.

## Migration Ledger

Create or update a source-to-target migration ledger. For every relevant source capability, record:

- Source file and capability.
- Classification: `reuse concept/test`, `rewrite`, `reject`, or `already superseded`.
- Target module and target test.
- Reason for the decision.
- Implementation and validation status.

The ledger must make it possible to verify that useful source behavior was either implemented, deliberately rejected, or shown to be superseded.

## Required Behavior

Preserve or rewrite, when not already superseded:

- Monotonic wall-clock timing around real invocation boundaries.
- Lossless Knowledge Base `activity[]` parsing, including unknown future activity types.
- Deterministic p50/p95/p99 and empty/single-value behavior.
- Cold/warm separation and reliability accounting that retains failed runs while excluding them from successful latency distributions.
- Per-stage and per-activity aggregation without false sequencing assumptions.
- Explicit units, sample counts, metric definitions, and unavailable-data reasons.
- Credential-free fake-adapter tests.
- Evaluation taxonomy and deterministic retrieval/citation/refusal metrics.
- Fixed-infrastructure versus variable-request cost categories using versioned user-supplied pricing profiles.

Reject these old behaviors:

- A duplicate `activity_capture` retrieval used only to obtain diagnostics.
- Summing parallel activity durations into a fabricated critical path.
- Presenting `total - sum(activity)` as proven orchestration overhead. Use qualified `unattributed_wall_time_ms` only when boundaries make the calculation valid.
- Hard-coded old orchestrator stages, preview APIs, customer identifiers, policy filenames/numbers, prices, volumes, or conclusions.

Use sanitized target-repository data and current normalized contracts.

## Execution

First identify what the running implementation has already completed and select the smallest missing source-to-target mapping. State one falsifiable local hypothesis and one focused check, implement that slice, and run its narrowest executable validation immediately. Then continue through adjacent missing mappings without undoing completed work.

Do not deploy resources, invoke paid services, run remote load tests, or modify the migration-source repository without explicit user approval.

In the final response, report the source-to-target mappings completed, files created or changed, focused validation results, rejected or superseded capabilities, and remaining migration items.
