# Benchmark Migration Ledger

Source inspected read-only on 2026-08-03:
`/home/brittanypugh/foundry-copilot-search-validate`.

The migration uses concepts and tests, not the old orchestrator, customer data,
policy identifiers, or report claims. All executable fixtures use this
repository's synthetic `10000`-`900100` policy identifiers.

| Source file and capability | Classification | Target module | Target test | Reason | Status |
| --- | --- | --- | --- | --- | --- |
| `src/latency/profiler.py`: monotonic public-boundary timing and exception capture | **reuse concept/test** | `src/benchmarking/adapters/*.py`, `runner.py` | `test_benchmarking_adapters.py` | Real adapter calls are timed once with `perf_counter`; exceptions become retained error rows. | **Implemented; 2026-08-03 passing** |
| `src/latency/profiler.py`: camel/snake activity normalization | **rewrite** | `src/benchmarking/activity.py`, `models.py` | `test_benchmarking_migration.py` | Normalize known numeric fields while preserving raw unknown fields through Pydantic extras. | **Implemented; passing** |
| `src/latency/profiler.py`: junk and unknown activity handling | **rewrite** | `src/benchmarking/activity.py` | `test_benchmarking_migration.py`, `test_benchmarking_phase1.py` | Ignore non-object junk; preserve unknown object activity types losslessly. | **Implemented; passing** |
| `src/latency/profiler.py`: activity grouping | **rewrite** | `src/benchmarking/activity.py` | `test_benchmarking_migration.py` | Aggregate record and token counts only; elapsed observations are not added into a critical path. | **Implemented; passing** |
| `src/latency/analysis.py`: linear percentile/statistics | **already superseded** | `src/benchmarking/aggregation.py` | `test_benchmarking_phase1.py` | Target already computes deterministic min/max/mean/stdev/p50/p95/p99, including single values. | **Implemented; passing** |
| `src/latency/analysis.py`: cold/warm aggregation | **rewrite** | `src/benchmarking/models.py`, `aggregation.py` | `test_benchmarking_migration.py` | Use explicit `temperature`; never infer coldness from list position. | **Implemented; passing** |
| `src/latency/analysis.py`: failed-run reliability accounting | **rewrite** | `src/benchmarking/aggregation.py` | `test_benchmarking_migration.py` | Retain all rows in count/error rate while excluding errors/timeouts from successful latency distributions. | **Implemented; passing** |
| `src/latency/report.py`: JSON/Markdown persistence | **already superseded** | `src/benchmarking/reporting.py`, `cli.py` | `test_benchmarking_phase1.py`, `test_benchmarking_cli.py` | Target emits versioned manifest, row JSONL, aggregate JSON, and Markdown with units/sample warnings. | **Implemented; passing** |
| `tests/test_latency_investigation.py`: fake orchestrator success/error tests | **reuse concept/test** | `src/benchmarking/adapters/agent.py`, `runner.py` | `test_benchmarking_adapters.py` | Fake async agents are called once; MCP-internal decomposition remains unavailable. | **Implemented; passing** |
| `evals/dataset.py`: eight-category taxonomy | **rewrite** | `src/benchmarking/evaluation.py` | `test_benchmarking_migration.py` | Uses target categories and sanitized stable source IDs, not source filenames/case IDs. | **Implemented; passing** |
| `evals/metrics.py`: recall@1/@3/@5 and MRR | **rewrite** | `src/benchmarking/evaluation.py`, `runner.py` | `test_benchmarking_migration.py`, `test_benchmarking_cli.py` | Compute ordered retrieval metrics from normalized `source_id` values. | **Implemented; passing** |
| `evals/metrics.py`: citation/refusal checks | **reuse concept/test** | `src/benchmarking/evaluation.py`, `src/evaluation/graders.py` | `test_benchmarking_migration.py` | Reuse target deterministic graders; do not copy source citation syntax or identifiers. | **Implemented; passing** |
| `evals/metrics.py`: optional faithfulness judge | **already superseded** | `src/evaluation/run_eval.py` | `test_evaluation_graders.py` | Existing optional `azure-ai-evaluation` integration remains cloud-optional; no manual source judge loop copied. | **Implemented previously; offline tests passing** |
| `docs/CostComparison.md`: fixed infrastructure versus variable request costs | **rewrite** | `src/benchmarking/costing.py`, `models.py` | `test_benchmarking_migration.py` | Versioned user rates retain formula, scope, assumptions, quantities, and exclusions. | **Implemented; passing** |
| `docs/CostComparison.md`: customer rates, volumes, region, and conclusions | **reject** | `docs/BenchmarkingDecisionSystem.md` | Documentation review plus migration tests | Source values are customer-specific and stale; target contains no universal live price. | **Rejected; verified 2026-08-03** |
| `scripts/investigate_latency.py`: duplicate `activity_capture` retrieve | **reject** | `src/benchmarking/adapters/agent.py` | `test_benchmarking_adapters.py` | A second retrieval cannot diagnose the first MCP invocation. | **Rejected; single-call test passing** |
| `models.py`/`analysis.py`: sum parallel `activity[].elapsedMs` | **reject** | `src/benchmarking/activity.py`, `models.py` | `test_benchmarking_migration.py` | Parallel service activities do not define a sequential critical path. | **Rejected; forbidden aggregate absent** |
| `models.py`/`report.py`: `total - activity_total` as orchestration overhead | **reject** | Normalized contracts omit this field | `test_benchmarking_migration.py` | Attribution is unproven without causally compatible trace boundaries. | **Rejected; forbidden field absent** |
| `scripts/investigate_latency.py`: old orchestrator/query loader | **reject** | `src/benchmarking/cli.py`, normalized adapters | `test_benchmarking_cli.py` | Target wraps current call sites and owns its manifest/cases. | **Replaced; CLI test passing** |
| `scripts/investigate_latency.py`: plausible Azure mock timings | **reject** | `experiments/datasets/synthetic-*` | `test_benchmarking_cli.py` | Synthetic fixtures verify contracts only and are explicitly labeled; no Azure performance claim is generated. | **Rejected; sanitized fixtures added** |
| `docs/RetrievalPatterns.md`: source Pattern A/B names and defaults | **reject** | `docs/RetrievalPatterns.md` | Existing routing tests | Names conflict with this target's published A/A2/B/C/Hosted narrative. | **Rejected; target narrative preserved** |

## Guardrails

- Controlled experiments, load tests, and production telemetry remain distinct.
- Client wall time, service-reported elapsed time, and child spans remain
  separate measurement types.
- No second retrieval is issued for MCP diagnostics.
- Reports never infer a sequential path from parallel service activities.
- Missing values remain `null` with an explicit reason.