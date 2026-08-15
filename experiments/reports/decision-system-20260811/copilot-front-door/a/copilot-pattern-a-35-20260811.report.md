# Experiment copilot-pattern-a-35-20260811

Controlled development experiment; not production telemetry or a load test.

- Pattern: `A`
- Invocation: `copilot_studio_direct_line:Default_AskHRPolicyAgent`
- Dataset: `copilot-hr-policy-v1` version `69d9e8e657698c4013b87e5fe9018c7bcc24b0fe7995b3abe4b5906ae5ce7539`
- Git commit: `853e2a083222ac927590f82b4bf3e3409fae73a1` (dirty: `True`)
- Samples: `35`
- Success rate: `100.0%`


## Client-observed latency

| Metric | Value |
| --- | ---: |
| Minimum | 11470.47 ms |
| Mean | 22463.32 ms |
| Standard deviation | 6270.84 ms |
| p50 | 22348.44 ms |
| p95 | 33687.35 ms |
| p99 | 37099.18 ms |
| Maximum | 38471.21 ms |

## Cold and warm latency

| Temperature | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Unspecified | 0 | n/a | n/a |

## Latency by query category

| Category | Samples | Mean | p95 |
| --- | ---: | ---: | ---: |
| `adversarial_out_of_domain` | 5 | 11942.50 ms | 13172.22 ms |
| `direct_fact` | 5 | 21702.00 ms | 22985.05 ms |
| `disambiguation` | 5 | 24973.26 ms | 27875.18 ms |
| `document_location` | 5 | 23370.67 ms | 24678.43 ms |
| `exact_lookup` | 5 | 20607.13 ms | 21386.79 ms |
| `multi_policy_synthesis` | 5 | 33914.70 ms | 37664.13 ms |
| `paraphrase_synonym` | 5 | 20733.01 ms | 23072.11 ms |

## Instrumented stage observations

| Stage | Observations | Mean | p95 |
| --- | ---: | ---: | ---: |
| Unavailable | 0 | n/a | n/a |

## Service activity observations

| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `message` | 35 | 0 | n/a | 0 | 0 | 0 |

## Estimated variable model cost

Variable model cost unavailable: not_configured. Priced invocations: 0/35.

Actual Azure charges are reconciled separately in Azure Cost Management; shared fixed resources are not attributed per request.

Each stage or activity duration is summarized as an independent observation. Parallel activity durations are never summed into a request critical path.