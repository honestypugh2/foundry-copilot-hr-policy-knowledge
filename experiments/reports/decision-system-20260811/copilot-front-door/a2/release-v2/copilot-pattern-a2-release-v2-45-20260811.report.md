# Experiment copilot-pattern-a2-release-v2-45-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A2`
- Invocation: `copilot_studio_direct_line:crf9c_askhrpolicyagentnew_jnP-W0`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `b0a2f04` (dirty: `True`)
- Samples: `45`
- Success rate: `not validly measured` (empty Direct Line responses; see runtime_note)


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 1635.67 ms |
| Mean | 1858.18 ms |
| Standard deviation | 413.92 ms |
| p50 | 1733.77 ms |
| p95 | 2844.80 ms |
| p99 | 3456.80 ms |
| Maximum | 3672.64 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 3 | 2433.41 ms | 3487.63 ms |
| `direct_fact` | 4 | 1740.08 ms | 1808.24 ms |
| `disambiguation` | 4 | 1748.58 ms | 1837.79 ms |
| `document_location` | 5 | 1947.80 ms | 2586.81 ms |
| `exact_lookup` | 4 | 1706.01 ms | 1790.04 ms |
| `multi_policy_synthesis` | 5 | 1746.69 ms | 1854.43 ms |
| `paraphrase_synonym` | 5 | 1714.81 ms | 1744.94 ms |
| `security_prompt_injection` | 3 | 1746.01 ms | 1830.29 ms |
| `security_secret_disclosure` | 3 | 2176.97 ms | 2924.85 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `message` | 36 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/45.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Copilot Studio native Evaluation

This is a separate replay through the same published agent and test set; it did not grade the timed Direct Line responses.

| Signal | Result |
| --- | ---: |
| General quality | 6/9 (66.7%) |
| Deterministic quality | 6/7 (85.7%) |
| Deterministic security | 2/2 (100.0%) |
| Native release ready | No |
| Native release blockers | General quality: 1 nondecisive native results |
| Evaluation run ID | `—` |
| Test set ID | `—` |
