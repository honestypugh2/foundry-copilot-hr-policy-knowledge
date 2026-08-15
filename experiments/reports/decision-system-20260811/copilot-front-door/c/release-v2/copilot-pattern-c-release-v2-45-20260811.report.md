# Experiment copilot-pattern-c-release-v2-45-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `C`
- Invocation: `copilot_studio_direct_line:crf9c_AskHRPolicyAgentC`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `45`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 8298.59 ms |
| Mean | 18247.13 ms |
| Standard deviation | 6343.71 ms |
| p50 | 19994.44 ms |
| p95 | 31789.18 ms |
| p99 | 32780.41 ms |
| Maximum | 33023.77 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 14211.21 ms | 14944.56 ms |
| `direct_fact` | 5 | 21697.71 ms | 23115.76 ms |
| `disambiguation` | 5 | 20529.71 ms | 22305.00 ms |
| `document_location` | 5 | 11906.84 ms | 12563.47 ms |
| `exact_lookup` | 5 | 20264.71 ms | 21223.46 ms |
| `multi_policy_synthesis` | 5 | 31697.09 ms | 32913.15 ms |
| `paraphrase_synonym` | 5 | 20212.06 ms | 20575.82 ms |
| `security_prompt_injection` | 5 | 9649.03 ms | 10781.70 ms |
| `security_secret_disclosure` | 5 | 14055.78 ms | 14892.15 ms |

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
| Compare meaning | 8/9 (88.9%) |
| Deterministic quality | 5/7 (71.4%) |
| Deterministic security | 2/2 (100.0%) |
| Native release ready | No |
| Native release blockers | General quality: 1 Error and 0 Invalid results; Compare meaning: 1 Error and 0 Invalid results |
| Evaluation run ID | `d093e463-72cf-430c-8d6c-fc522005b21a` |
| Test set ID | `e7bbf8fb-fcd9-40ae-bbec-fa07086e99e5` |
