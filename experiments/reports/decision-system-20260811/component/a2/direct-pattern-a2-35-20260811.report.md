# Experiment direct-pattern-a2-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A2`
- Invocation: `direct_knowledge_base_retrieve`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `97.1%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 4894.68 ms |
| Mean | 7938.95 ms |
| Standard deviation | 3841.01 ms |
| p50 | 6831.19 ms |
| p95 | 10661.96 ms |
| p99 | 22488.89 ms |
| Maximum | 28148.63 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 4 | 9715.51 ms | 10862.96 ms |
| `direct_fact` | 5 | 6654.26 ms | 7577.00 ms |
| `disambiguation` | 5 | 6617.57 ms | 8440.79 ms |
| `document_location` | 5 | 7252.88 ms | 9757.32 ms |
| `exact_lookup` | 5 | 6714.85 ms | 7640.39 ms |
| `multi_policy_synthesis` | 5 | 11289.38 ms | 24152.75 ms |
| `paraphrase_synonym` | 5 | 7683.50 ms | 10114.41 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `agenticReasoning` | 34 | 0 | n/a | 0 | 0 | 1162682 |
| `modelQueryPlanning` | 68 | 68 | 2107.00 ms | 116811 | 7112 | 0 |
| `searchIndex` | 205 | 205 | 0.00 ms | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/35.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.