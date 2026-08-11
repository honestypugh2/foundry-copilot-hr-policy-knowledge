# Experiments

This directory contains the versioned inputs and selected evidence for the HR
policy architecture benchmark. It supports reproducible comparisons across
retrieval modes without treating local smoke tests, model estimates, and Azure
billing data as interchangeable evidence.

## Directory map

| Path | Purpose | Tracked by default |
| --- | --- | --- |
| `datasets/` | Versioned benchmark cases and deterministic evaluation specifications | Yes |
| `manifests/` | Experiment configuration, provenance, sample counts, and retrieval mode | Yes |
| `pricing/` | Versioned model-price assumptions used for per-run estimates | Yes |
| `kql/` | Bounded Azure Monitor and Application Insights query templates | Yes |
| `reports/` | Generated rows and aggregate reports | No; only reviewed fixtures and curated publications |
| `cost-reconciliation/` | Local Azure Cost Management exports | No |

The schemas and runner implementation live in
[`src/benchmarking/`](../src/benchmarking/). Generated outputs use four files:

- `*.manifest.json`: the resolved configuration and source provenance.
- `*.results.jsonl`: one normalized record per measured case invocation.
- `*.report.json`: machine-readable aggregates and provenance.
- `*.report.md`: a human-readable summary of the same aggregate report.

An evaluated publication can also contain `*.evaluation.json`. Evaluation is a
separate same-configuration replay because measured benchmark rows intentionally
exclude answer text.

## Evidence levels

Not every artifact supports the same claim.

| Evidence | Valid use | Invalid use |
| --- | --- | --- |
| Synthetic fixture | Schema, API, UI, and report-generation tests | Azure latency, quality, or cost claims |
| Controlled live run | Comparable success, client latency, service-reported tokens, and estimated variable model cost | Production SLOs or exact billed cost |
| Evaluation replay | Deterministic quality/security gates and supplemental judge scores | Retrospective grading of latency rows |
| Azure telemetry | Operational traces, failures, capacity, and service behavior | Reconstructing fields that were not emitted |
| Cost Management export | Shared-resource billed-cost reconciliation | Per-request or per-mode attribution without matching dimensions |

Deterministic gates remain authoritative when an LLM judge disagrees. Judge
means, pass rates, and calibration are supplemental signals and must remain
visible rather than replacing negative findings.

## Offline smoke test

The credential-free fixture validates contracts and report generation:

```bash
source .venv/bin/activate
python -m src.benchmarking.cli \
  --manifest experiments/manifests/synthetic-direct-search.json \
  --cases experiments/datasets/synthetic-migration-smoke.json \
  --fixture-responses experiments/datasets/synthetic-direct-search-responses.json \
  --output-dir experiments/reports/synthetic-direct-search
```

These timings are local fixture behavior, not Azure performance evidence.

## Controlled Agent Framework run

Live runs require the expected Azure tenant, subscription, and principal values
in the local environment. The CLI verifies that identity before invoking Azure.
Activate the project virtual environment, then run a manifest through the local
Agent Framework path:

```bash
source .venv/bin/activate
python -m src.benchmarking.cli \
  --manifest experiments/manifests/agent-framework-tool-priced-35-20260810.json \
  --cases experiments/datasets/copilot-hr-policy-v1.json \
  --output-dir experiments/reports/local-tool-run \
  --pricing-profile experiments/pricing/azure-gpt-5-mini-global-standard-cache-aware-2025-08-01.json \
  --agent-framework
```

Before a new controlled run, copy or update the manifest so these fields match
the actual run:

- `git_commit` and `dirty_worktree`
- dataset, corpus, and index fingerprints
- model deployment and version
- retrieval mode and invocation path
- warmups, measured repetitions, concurrency, and timeout
- pricing profile identifier

Do not publish a dirty-worktree run as reproducible evidence. Keep concurrency,
sample count, model configuration, and workload fixed when comparing modes.

## Quality and security evaluation

Attach deterministic gates and calibrated Foundry judge scores after the
controlled run:

```bash
source .venv/bin/activate
python -m src.benchmarking.evaluation_attachment \
  --manifest experiments/reports/<run>/<mode>/<experiment>.manifest.json \
  --cases experiments/datasets/copilot-hr-policy-v1.json \
  --evaluation-spec experiments/datasets/copilot-hr-policy-v1-evaluation.json \
  --report experiments/reports/<run>/<mode>/<experiment>.report.json \
  --output-dir experiments/reports/<run>/<mode>/evaluation
```

This command performs paid model calls. It writes a sanitized evaluation
summary and attaches aggregate quality, security, judge, and calibration fields
to the JSON and Markdown reports. Raw prompts and answers are not part of the
evaluation summary.

## Publication policy

`reports/` and `cost-reconciliation/` are ignored by default. A report may be
explicitly allowlisted in the repository `.gitignore` only after review.

Commit a publication bundle only when:

1. The manifest identifies a clean source commit and the actual environment.
2. Every expected case completed, sample counts are adequate, and priced runs
   have complete pricing coverage.
3. Quality and security failures are retained rather than tuned away.
4. Judge coverage and deterministic-to-judge calibration are present.
5. JSONL and JSON artifacts contain no raw query, answer, prompt, retrieved
   document content, credentials, or connection strings.
6. Staging manifests, raw judge input/output, and Cost Management exports are
   excluded.
7. A secret scan and focused report-integrity check pass.

Response, conversation, trace, and evaluation identifiers can support lineage,
but they are not credentials. Review them as operational metadata before making
a repository public.

## Current publication

[`reports/publication-9c94215-20260810/`](reports/publication-9c94215-20260810/)
contains 35 measured invocations for each retrieval mode from source commit
`9c94215507af1256b7385038c7b2ce1c1064d2d3`:

- [`tool/`](reports/publication-9c94215-20260810/tool/)
- [`context-semantic/`](reports/publication-9c94215-20260810/context-semantic/)
- [`context-agentic/`](reports/publication-9c94215-20260810/context-agentic/)

All three runs completed successfully and have full variable model-price
coverage. Their deterministic quality/security results and calibrated judge
scores are attached to each report. Preserve the report qualifications:

- Latency is client-observed controlled-development latency, not a production
  SLO or load test.
- Variable model cost is an estimate from the named pricing profile, not an
  Azure invoice.
- Evaluation is a separate replay and does not grade the measured latency rows.
- Security and quality failures remain part of the evidence.

## Validation

Run the benchmark tests from the project virtual environment:

```bash
source .venv/bin/activate
pytest -q
ruff check src/benchmarking tests
```

Useful supporting documentation:

- [`docs/PatternSetupAndBenchmarkGuide.md`](../docs/PatternSetupAndBenchmarkGuide.md)
- [`docs/CopilotStudioBenchmarking.md`](../docs/CopilotStudioBenchmarking.md)
- [`datasets/README.md`](datasets/README.md)
- [`kql/README.md`](kql/README.md)