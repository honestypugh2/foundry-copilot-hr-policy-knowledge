# Experiment direct-pattern-b-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `B`
- Invocation: `foundry_responses_agent_mcp`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 25430.96 ms |
| Mean | 51620.54 ms |
| Standard deviation | 106785.97 ms |
| p50 | 30942.47 ms |
| p95 | 54202.17 ms |
| p99 | 467385.28 ms |
| Maximum | 672492.58 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 29546.43 ms | 33352.61 ms |
| `direct_fact` | 5 | 30610.26 ms | 38500.64 ms |
| `disambiguation` | 5 | 33021.31 ms | 38404.65 ms |
| `document_location` | 5 | 157588.05 ms | 544311.36 ms |
| `exact_lookup` | 5 | 29449.18 ms | 31843.32 ms |
| `multi_policy_synthesis` | 5 | 37282.34 ms | 42411.13 ms |
| `paraphrase_synonym` | 5 | 43846.20 ms | 64940.47 ms |

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