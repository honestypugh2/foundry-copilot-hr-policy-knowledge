# Experiment agent-framework-tool-publication-9c94215-35-20260810

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `agent_framework_local:tool`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `9c94215507af1256b7385038c7b2ce1c1064d2d3` (dirty: `False`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 10857.16 ms |
| Mean | 17441.59 ms |
| Standard deviation | 5040.40 ms |
| p50 | 16364.77 ms |
| p95 | 25758.05 ms |
| p99 | 32408.94 ms |
| Maximum | 35152.25 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 12757.62 ms | 13653.93 ms |
| `direct_fact` | 5 | 16782.61 ms | 20357.25 ms |
| `disambiguation` | 5 | 19855.46 ms | 32067.84 ms |
| `document_location` | 5 | 17315.33 ms | 18749.61 ms |
| `exact_lookup` | 5 | 16772.23 ms | 21146.21 ms |
| `multi_policy_synthesis` | 5 | 23357.32 ms | 26704.94 ms |
| `paraphrase_synonym` | 5 | 15250.60 ms | 20438.86 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

| Metric | Value |
| --- | ---: |
| Mean per invocation | 0.00330519 USD |
| Run total | 0.11568150 USD |
| Priced invocations | 35 |
| Pricing profile | `azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` |

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Quality and security evaluation

Evaluation is a separate same-configuration replay; it does not retroactively grade the measured latency rows. Deterministic gates remain authoritative and judge scores are supplemental.

| Signal | Result |
| --- | ---: |
| Deterministic quality | 7/7 (100.0%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 4.43/5 |
| Judge intent-resolution mean | 5.00/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
