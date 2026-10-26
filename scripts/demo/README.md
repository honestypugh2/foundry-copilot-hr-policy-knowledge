# Demo script interfaces

These modules exercise repository-owned retrieval and gateway paths against live
Azure resources. They are integration utilities, not unit tests or comparative
benchmark evidence. Mocked regression tests are in [tests/](../../tests/).

## Retrieval scripts

| Module | Code path | Scope |
| --- | --- | --- |
| [test_pattern_a.py](test_pattern_a.py) | Direct hybrid index search | Glossary expansion and deterministic rendering of retrieved policy content |
| [test_pattern_b.py](test_pattern_b.py) | [HRPolicyAgent](../../src/agents/hr_policy_agent.py) | Managed Foundry prompt agent with Knowledge Base MCP retrieval |
| [test_pattern_c.py](test_pattern_c.py) | Document locator | Hybrid search projected into policy/document link metadata |
| [test_pattern_hosted.py](test_pattern_hosted.py) | [Agent Framework HRPolicyAgent](../../src/agents/hr_policy_agent_af.py) | In-process agent invocation, not the deployed hosted application endpoint |
| [demo_decision_tree.py](demo_decision_tree.py) | The four paths above | Prints single-run results and latency observations |
| [_common.py](_common.py) | Shared helpers | Environment checks, timing, and result formatting |

Pattern A2 has no local demo module because Copilot Studio owns its synthesis.
Its repository integration is covered by the Direct Line benchmark adapter.

The individual pattern modules accept `--question` / `-q`. The decision-tree
module accepts `--content`, `--locator`, `--skip-b`, and `--skip-hosted`.
Example interface shapes:

```bash
python -m scripts.demo.test_pattern_a -q "What is the dress code policy?"
python -m scripts.demo.test_pattern_b -q "What is the parental leave policy?"
python -m scripts.demo.demo_decision_tree --skip-hosted
```

Pattern B initializes the managed prompt agent before invocation. Its fallback
path can return local-search results when Foundry is unavailable; an exit code
of zero alone does not prove the managed-agent path ran.
The hosted-pattern module exercises local Agent Framework code rather than the
platform-managed `ResponsesHostServer` runtime or its Agent 365 exporter.

## Environment contract

The scripts load the repository's ignored `.env` through `python-dotenv`.

| Variable | Consumer | Meaning |
| --- | --- | --- |
| `AZURE_SEARCH_ENDPOINT` | Retrieval scripts | Search service endpoint |
| `AZURE_SEARCH_API_KEY` | Key-enabled retrieval paths | Optional key; identity credentials are used on identity-enabled paths |
| `AZURE_SEARCH_INDEX_NAME` | Retrieval scripts | Index name, default `hr-policy-index` |
| `AZURE_AI_PROJECT_ENDPOINT` | Pattern B / in-process Agent Framework | Foundry project endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model-backed paths | Chat deployment selection |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Tracing / preflight | Azure Monitor destination or presence check, not an Agent 365 credential |

The retrieval scripts assume a populated index. Pattern B additionally depends
on the managed agent and Knowledge Base MCP configuration owned by
[create_foundry_agent.py](../../src/agents/create_foundry_agent.py).
Full pattern ownership is described in
[PatternSetupAndBenchmarkGuide.md](../../docs/PatternSetupAndBenchmarkGuide.md).

## Gateway and traffic utilities

| File | Behavior |
| --- | --- |
| [gateway_demo.py](gateway_demo.py) | Calls the APIM model route with a consumer subscription; prints status, usage, remaining tokens, and latency |
| [gateway_queries.kql](gateway_queries.kql) | Queries token metrics, gateway status counts, 429s, and LLM logs |
| [preflight.py](preflight.py) | Checks subscription, backend health, Foundry verification, index count, both gateway keys, and App Insights configuration |
| [warmup.sh](warmup.sh) | Generates timestamped Pattern B and gateway traffic, including synthetic jailbreak prompts |

The gateway module depends on the
[APIM add-on](../../infra/addons/apim-ai-gateway/README.md) and these variables:
`APIM_GATEWAY_URL`, `APIM_KEY_ASSET_AGENT`, `APIM_KEY_PARTNER_APP`,
`APIM_API_VERSION` (default `2024-10-21`), and `APIM_DEPLOYMENT_NAME`
(default `gpt-5-mini`).

Example CLI interfaces:

```bash
python -m scripts.demo.gateway_demo --consumer asset-agent -q "Describe a fictional leave policy."
python -m scripts.demo.gateway_demo --consumer partner-app --burst 15
python -m scripts.demo.gateway_demo --consumer asset-agent --jailbreak
```

`--burst` sends sequential requests and does not guarantee a 429.
`--jailbreak` sends a fixed test prompt and reports the returned filter status;
it does not create or verify Defender alerts. Gateway requests do not invoke a
published agent. The implementation reference is
[DemoRunbook-PWW.md](../../docs/DemoRunbook-PWW.md).

## Agent 365 configuration diagnostic

[agent365_preflight.py](agent365_preflight.py) is a separate read-only diagnostic.
It checks the account collection state, Agent 365 observability service,
supplied hosted identities' write assignments, and Defender configuration.
It does not send conversations, grant permissions, or verify remote ingestion.

```text
python -m scripts.demo.agent365_preflight \
  --hosted-agent-principal-id <agent-identity-object-id>
```

The account defaults to the parent of `AZURE_AI_PROJECT_RESOURCE_ID`, with
`--account-resource-id` as an override. The hosted-principal flag is repeatable.
Expected tenant/subscription variables constrain the active Azure CLI context
when configured.

Telemetry ownership, privacy, and security attribution are documented in
[Agent365Observability.md](../../docs/Agent365Observability.md).

## Exit-code semantics

| Utility | Meaning |
| --- | --- |
| Retrieval/decision-tree scripts | `0`: requested path returned successfully, including any supported fallback; `1`: failure; `2`: missing required configuration; `130`: interrupted demo where handled |
| `gateway_demo.py` | `2`: missing gateway URL/key; otherwise `0` after the request loop, including printed HTTP or transport errors |
| `preflight.py` | `0`: dependency checks pass; `1`: one or more fail; HTTP 429 counts as gateway reachability |
| `agent365_preflight.py` | `1`: configuration/read failure; `2`: no failure but visibility or coverage unknown; successful reads currently always leave ingestion unknown |
| `warmup.sh` | Continues after individual failures; does not compute an aggregate test result |

The gateway and dependency preflight issue live model requests and can incur
usage charges. Agent 365 preflight performs configuration reads only.

## Related code documentation

- [RetrievalPatterns.md](../../docs/RetrievalPatterns.md)
- [LabCoverage.md](../../docs/LabCoverage.md)
- [CopilotStudioLookupRouting.md](../../docs/CopilotStudioLookupRouting.md)
