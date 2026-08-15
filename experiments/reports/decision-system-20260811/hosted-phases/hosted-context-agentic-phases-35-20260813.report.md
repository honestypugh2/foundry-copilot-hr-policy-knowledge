# Experiment hosted-context-agentic-phases-35-20260813

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `agent_framework_local:context-agentic`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 16030.70 ms |
| Mean | 25816.59 ms |
| Standard deviation | 9553.91 ms |
| p50 | 23506.98 ms |
| p95 | 45606.48 ms |
| p99 | 56448.26 ms |
| Maximum | 56975.85 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 24846.40 ms | 34517.09 ms |
| `direct_fact` | 5 | 32598.34 ms | 51459.95 ms |
| `disambiguation` | 5 | 22112.27 ms | 28406.87 ms |
| `document_location` | 5 | 29287.81 ms | 51489.11 ms |
| `exact_lookup` | 5 | 20246.75 ms | 22183.36 ms |
| `multi_policy_synthesis` | 5 | 30726.13 ms | 40158.45 ms |
| `paraphrase_synonym` | 5 | 20898.46 ms | 26980.60 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `agenticReasoning` | 35 | 0 | n/a | 0 | 0 | 1270351 |
| `modelQueryPlanning` | 70 | 70 | 2085.00 ms | 179434 | 6491 | 0 |
| `searchIndex` | 224 | 224 | 0.00 ms | 0 | 0 | 0 |

## Estimated variable model cost

| Metric | Value |
| --- | ---: |
| Mean per invocation | 0.00320579 USD |
| Run total | 0.11220275 USD |
| Priced invocations | 35 |
| Pricing profile | `azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` |

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Quality and security evaluation

Evaluation is a separate same-configuration replay; it does not retroactively grade the measured latency rows. Deterministic gates remain authoritative and judge scores are supplemental.

| Signal | Result |
| --- | ---: |
| Deterministic quality | 6/7 (85.7%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 5.00/5 |
| Judge intent-resolution mean | 4.57/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
