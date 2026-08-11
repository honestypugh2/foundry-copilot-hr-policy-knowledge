# Experiment agent-framework-context-agentic-publication-9c94215-35-20260810

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `agent_framework_local:context-agentic`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `9c94215507af1256b7385038c7b2ce1c1064d2d3` (dirty: `False`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 12618.87 ms |
| Mean | 24111.93 ms |
| Standard deviation | 7484.27 ms |
| p50 | 21959.93 ms |
| p95 | 34668.61 ms |
| p99 | 47599.54 ms |
| Maximum | 54010.91 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 24063.30 ms | 33518.06 ms |
| `direct_fact` | 5 | 24220.46 ms | 29835.05 ms |
| `disambiguation` | 5 | 24963.11 ms | 28805.19 ms |
| `document_location` | 5 | 22314.14 ms | 27453.71 ms |
| `exact_lookup` | 5 | 19778.96 ms | 20992.30 ms |
| `multi_policy_synthesis` | 5 | 35017.59 ms | 50239.51 ms |
| `paraphrase_synonym` | 5 | 18425.97 ms | 22505.15 ms |

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
| Mean per invocation | 0.00324570 USD |
| Run total | 0.11359945 USD |
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
| Judge intent-resolution mean | 5.00/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
