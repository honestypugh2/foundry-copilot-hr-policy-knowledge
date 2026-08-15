# Experiment copilot-pattern-a-release-v2-45-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A`
- Invocation: `copilot_studio_direct_line:Default_AskHRPolicyAgent`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `45`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 7354.36 ms |
| Mean | 19345.77 ms |
| Standard deviation | 7287.72 ms |
| p50 | 20458.63 ms |
| p95 | 32920.17 ms |
| p99 | 36285.93 ms |
| Maximum | 37687.72 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 10918.72 ms | 12711.80 ms |
| `direct_fact` | 5 | 21947.83 ms | 23684.96 ms |
| `disambiguation` | 5 | 21784.78 ms | 25999.00 ms |
| `document_location` | 5 | 20753.00 ms | 22244.31 ms |
| `exact_lookup` | 5 | 21265.79 ms | 22529.80 ms |
| `multi_policy_synthesis` | 5 | 33895.21 ms | 37050.54 ms |
| `paraphrase_synonym` | 5 | 21532.82 ms | 22570.09 ms |
| `security_prompt_injection` | 5 | 8642.36 ms | 9510.89 ms |
| `security_secret_disclosure` | 5 | 13371.43 ms | 14308.31 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `message` | 45 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/45.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Copilot Studio native Evaluation

This is a separate replay through the same published agent and test set; it did not grade the timed Direct Line responses.

| Signal | Result |
| --- | ---: |
| General quality | 6/9 (66.7%) |
| Compare meaning | 7/9 (77.8%) |
| Deterministic quality | 6/7 (85.7%) |
| Deterministic security | 2/2 (100.0%) |
| Native release ready | No |
| Native release blockers | General quality: 1 Error and 0 Invalid results; Compare meaning: 1 Error and 0 Invalid results |
| Evaluation run ID | `85f6486d-48eb-4ba2-9764-281af8f2aa22` |
| Test set ID | `edadb7d2-82df-422b-a563-6c99bbb43c4b` |
