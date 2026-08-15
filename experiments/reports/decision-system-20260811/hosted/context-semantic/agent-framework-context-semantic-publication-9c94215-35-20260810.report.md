# Experiment agent-framework-context-semantic-publication-9c94215-35-20260810

Controlled development experiment; not production telemetry or a load test.

- Pattern: `Hosted`
- Invocation: `agent_framework_local:context-semantic`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `9c94215507af1256b7385038c7b2ce1c1064d2d3` (dirty: `False`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 8445.34 ms |
| Mean | 20725.96 ms |
| Standard deviation | 9344.29 ms |
| p50 | 17485.80 ms |
| p95 | 38167.89 ms |
| p99 | 44553.57 ms |
| Maximum | 46809.35 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 20278.78 ms | 25504.86 ms |
| `direct_fact` | 5 | 14448.07 ms | 16699.52 ms |
| `disambiguation` | 5 | 22849.69 ms | 41713.46 ms |
| `document_location` | 5 | 23963.54 ms | 36097.77 ms |
| `exact_lookup` | 5 | 18931.25 ms | 35332.60 ms |
| `multi_policy_synthesis` | 5 | 31001.39 ms | 33272.26 ms |
| `paraphrase_synonym` | 5 | 13608.98 ms | 20977.61 ms |

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
| Mean per invocation | 0.00309650 USD |
| Run total | 0.10837765 USD |
| Priced invocations | 35 |
| Pricing profile | `azure-gpt-5-mini-global-standard-cache-aware:2025-08-01` |

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.
## Quality and security evaluation

Evaluation is a separate same-configuration replay; it does not retroactively grade the measured latency rows. Deterministic gates remain authoritative and judge scores are supplemental.

| Signal | Result |
| --- | ---: |
| Deterministic quality | 5/7 (71.4%) |
| Deterministic security | 2/2 (100.0%) |
| Judge relevance mean | 4.86/5 |
| Judge intent-resolution mean | 4.57/5 |
| Judge model | `gpt-5-mini` |
| Judge rubric | `responses-relevance-intent-v1` |
