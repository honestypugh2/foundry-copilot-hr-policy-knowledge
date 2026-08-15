# Experiment direct-pattern-a-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A`
- Invocation: `direct_search_sdk`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 332.39 ms |
| Mean | 507.27 ms |
| Standard deviation | 127.57 ms |
| p50 | 482.69 ms |
| p95 | 682.96 ms |
| p99 | 881.97 ms |
| Maximum | 984.12 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 410.53 ms | 505.71 ms |
| `direct_fact` | 5 | 575.90 ms | 680.56 ms |
| `disambiguation` | 5 | 570.33 ms | 664.27 ms |
| `document_location` | 5 | 514.05 ms | 628.63 ms |
| `exact_lookup` | 5 | 429.73 ms | 525.38 ms |
| `multi_policy_synthesis` | 5 | 560.89 ms | 891.11 ms |
| `paraphrase_synonym` | 5 | 489.45 ms | 559.68 ms |

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