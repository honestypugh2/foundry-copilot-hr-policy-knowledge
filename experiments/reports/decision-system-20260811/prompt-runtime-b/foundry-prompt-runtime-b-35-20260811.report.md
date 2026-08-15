# Experiment foundry-prompt-runtime-b-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `B`
- Invocation: `foundry_hosted_agent:HRPolicyAgent`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `fe3a17c` (dirty: `True`)
- Samples: `45`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 934.64 ms |
| Mean | 26114.52 ms |
| Standard deviation | 13419.86 ms |
| p50 | 24229.40 ms |
| p95 | 43205.86 ms |
| p99 | 65255.54 ms |
| Maximum | 75593.90 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 24044.89 ms | 31351.93 ms |
| `direct_fact` | 5 | 25534.28 ms | 31609.92 ms |
| `disambiguation` | 5 | 26316.42 ms | 29946.21 ms |
| `document_location` | 5 | 22231.49 ms | 24002.17 ms |
| `exact_lookup` | 5 | 27986.07 ms | 42057.39 ms |
| `multi_policy_synthesis` | 5 | 41317.16 ms | 69113.47 ms |
| `paraphrase_synonym` | 5 | 26551.16 ms | 30406.06 ms |
| `security_prompt_injection` | 5 | 1070.51 ms | 1305.11 ms |
| `security_secret_disclosure` | 5 | 39978.72 ms | 49676.15 ms |

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
| Judge relevance mean | 4.86/5 |
| Judge intent-resolution mean | 4.71/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
