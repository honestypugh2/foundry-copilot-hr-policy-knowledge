# Experiment foundry-hosted-runtime-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `foundry_hosted_agent:hr-policy-agent`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 17464.06 ms |
| Mean | 25948.14 ms |
| Standard deviation | 6102.74 ms |
| p50 | 23942.75 ms |
| p95 | 39528.24 ms |
| p99 | 40338.49 ms |
| Maximum | 40682.97 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 20813.43 ms | 25518.37 ms |
| `direct_fact` | 5 | 26346.49 ms | 31099.79 ms |
| `disambiguation` | 5 | 28190.44 ms | 38296.32 ms |
| `document_location` | 5 | 23154.70 ms | 25189.56 ms |
| `exact_lookup` | 5 | 23782.39 ms | 28600.74 ms |
| `multi_policy_synthesis` | 5 | 33886.39 ms | 39284.31 ms |
| `paraphrase_synonym` | 5 | 25463.12 ms | 36399.14 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_exposed. Priced invocations: 0/35.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Quality and security evaluation

Evaluation is a separate replay against the deployed hosted agent runtime; it does not retroactively grade the measured latency rows. Deterministic gates remain authoritative and judge scores are supplemental.

| Signal | Result |
| --- | ---: |
| Deterministic quality | 7/7 (100.0%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 5.00/5 |
| Judge intent-resolution mean | 4.86/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
