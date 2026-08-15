# Experiment foundry-hosted-runtime-release-v2-45-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `foundry_hosted_agent:hr-policy-agent`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `fe3a17c` (dirty: `True`)
- Samples: `45`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 4901.81 ms |
| Mean | 27363.82 ms |
| Standard deviation | 8330.76 ms |
| p50 | 28338.81 ms |
| p95 | 41087.57 ms |
| p99 | 42376.75 ms |
| Maximum | 43168.48 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 25502.75 ms | 28866.39 ms |
| `direct_fact` | 5 | 27095.79 ms | 29111.06 ms |
| `disambiguation` | 5 | 29211.11 ms | 33741.36 ms |
| `document_location` | 5 | 33751.30 ms | 41703.01 ms |
| `exact_lookup` | 5 | 30701.28 ms | 39526.91 ms |
| `multi_policy_synthesis` | 5 | 34052.29 ms | 39851.83 ms |
| `paraphrase_synonym` | 5 | 21501.45 ms | 31434.61 ms |
| `security_prompt_injection` | 5 | 11942.77 ms | 12385.53 ms |
| `security_secret_disclosure` | 5 | 32515.68 ms | 39544.97 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_exposed. Priced invocations: 0/45.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Quality and security evaluation

Evaluation is a separate replay against the deployed hosted agent runtime; it does not retroactively grade the measured latency rows. Deterministic gates remain authoritative and judge scores are supplemental.

| Signal | Result |
| --- | ---: |
| Deterministic quality | 5/7 (71.4%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 4.43/5 |
| Judge intent-resolution mean | 4.71/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
