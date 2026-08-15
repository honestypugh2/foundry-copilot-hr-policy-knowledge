# Experiment foundry-hosted-runtime-agentic-35-20260812

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
| Minimum | 22262.55 ms |
| Mean | 48359.93 ms |
| Standard deviation | 105814.37 ms |
| p50 | 29112.93 ms |
| p95 | 48432.54 ms |
| p99 | 458347.95 ms |
| Maximum | 664087.41 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 25406.96 ms | 28528.45 ms |
| `direct_fact` | 5 | 25618.50 ms | 27729.38 ms |
| `disambiguation` | 5 | 30443.77 ms | 35319.92 ms |
| `document_location` | 5 | 33453.14 ms | 37728.10 ms |
| `exact_lookup` | 5 | 29189.48 ms | 31499.22 ms |
| `multi_policy_synthesis` | 5 | 167603.76 ms | 543064.20 ms |
| `paraphrase_synonym` | 5 | 26803.87 ms | 29443.29 ms |

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
| Deterministic quality | 6/7 (85.7%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 4.86/5 |
| Judge intent-resolution mean | 4.57/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
