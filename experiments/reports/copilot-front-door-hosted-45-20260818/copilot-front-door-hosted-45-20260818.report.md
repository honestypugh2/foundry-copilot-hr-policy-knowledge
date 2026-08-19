# Experiment copilot-front-door-hosted-45-20260818

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `copilot_studio_direct_line:crf9c_AskHRPolicyAgentB`
- Dataset: `copilot-hr-policy-release-v2` version `sha256:b0ddc82ddec2e5eb7235182dd77ad75e39039d9e1cf9086bde258897982e09e2`
- Git commit: `80403ac7b2fd8878280f993e18ab7830f322a31f` (dirty: `False`)
- Samples: `45`
- Success rate: `86.7%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 6575.03 ms |
| Mean | 30193.11 ms |
| Standard deviation | 18161.86 ms |
| p50 | 34701.16 ms |
| p95 | 55458.87 ms |
| p99 | 63083.11 ms |
| Maximum | 63106.32 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 10642.90 ms | 12984.90 ms |
| `direct_fact` | 4 | 45792.74 ms | 53100.92 ms |
| `disambiguation` | 4 | 55332.49 ms | 63097.16 ms |
| `document_location` | 4 | 42209.91 ms | 52040.98 ms |
| `exact_lookup` | 4 | 34728.87 ms | 35533.89 ms |
| `multi_policy_synthesis` | 3 | 46297.58 ms | 52360.18 ms |
| `paraphrase_synonym` | 5 | 38368.62 ms | 40073.06 ms |
| `security_prompt_injection` | 5 | 7791.53 ms | 9004.15 ms |
| `security_secret_disclosure` | 5 | 8473.46 ms | 10315.65 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `message` | 39 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/45.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.