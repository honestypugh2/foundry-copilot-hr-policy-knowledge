# Experiment synthetic-direct-search

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A`
- Invocation: `direct_search_fixture`
- Dataset: `synthetic-migration-smoke` version `1.0`
- Git commit: `synthetic` (dirty: `False`)
- Samples: `6`
- Success rate: `100.0%`

> Only 6 measured samples; percentile estimates are unstable.


> Synthetic fixture mode: timing values measure only local contract execution and are not Azure performance evidence.

## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 0.00 ms |
| Mean | 0.00 ms |
| Standard deviation | 0.00 ms |
| p50 | 0.00 ms |
| p95 | 0.00 ms |
| p99 | 0.00 ms |
| Maximum | 0.00 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `direct_fact` | 3 | 0.00 ms | 0.00 ms |
| `document_location` | 3 | 0.00 ms | 0.00 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.