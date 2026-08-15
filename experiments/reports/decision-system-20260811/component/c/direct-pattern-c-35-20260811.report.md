# Experiment direct-pattern-c-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `C`
- Invocation: `deterministic_lookup`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 346.86 ms |
| Mean | 502.34 ms |
| Standard deviation | 113.97 ms |
| p50 | 484.44 ms |
| p95 | 735.82 ms |
| p99 | 835.52 ms |
| Maximum | 871.96 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 531.74 ms | 640.88 ms |
| `direct_fact` | 5 | 500.35 ms | 569.18 ms |
| `disambiguation` | 5 | 395.57 ms | 454.16 ms |
| `document_location` | 5 | 512.93 ms | 687.66 ms |
| `exact_lookup` | 5 | 557.43 ms | 804.91 ms |
| `multi_policy_synthesis` | 5 | 482.94 ms | 534.41 ms |
| `paraphrase_synonym` | 5 | 535.45 ms | 721.47 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/35.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.