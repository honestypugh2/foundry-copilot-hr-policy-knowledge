# AI gateway demo implementation

The PWW demo code illustrates model-access governance with synthetic HR prompts.
Its APIM infrastructure is a standalone
[add-on](../infra/addons/apim-ai-gateway/README.md), independent of the main azd
infrastructure. Gateway resources use the `pwwdemo` prefix where supported and
the APIM service is tagged `purpose=pww-demo`.

## Request paths

| Entry point | Request destination | Behavior |
| --- | --- | --- |
| [gateway_demo.py](../scripts/demo/gateway_demo.py) | APIM model API | Sends chat completions under a selected consumer's subscription |
| [test_pattern_b.py](../scripts/demo/test_pattern_b.py) | Managed prompt agent via the project Responses API | Exercises Pattern B retrieval and answer generation |
| [warmup.sh](../scripts/demo/warmup.sh) | Both paths above | Generates timestamped synthetic traffic |
| [preflight.py](../scripts/demo/preflight.py) | Backend, Search, Foundry verification, and APIM | Checks demo dependencies; APIM checks issue model requests |
| [agent365_preflight.py](../scripts/demo/agent365_preflight.py) | ARM, Graph, and Defender configuration | Read-only Agent 365 configuration checks; no model requests |

The APIM model route is:

```text
POST {APIM_GATEWAY_URL}/openai/deployments/{APIM_DEPLOYMENT_NAME}/chat/completions
     ?api-version={APIM_API_VERSION}
```

The gateway root is not a dashboard and has no configured GET operation.
A browser request to `/` can therefore return 404 even when the API is available.

## Gateway policies

[policy.xml](../infra/addons/apim-ai-gateway/policy.xml) applies these inbound
policies to the model API:

- Subscription authentication uses the incoming `api-key` header. The policy
  deletes that header before forwarding the request.
- `set-backend-service` routes to the existing model endpoint.
- `authentication-managed-identity` obtains backend authorization for
  `https://cognitiveservices.azure.com`; the model call uses no model API key.
- `llm-token-limit` enforces 2,000 tokens per minute per APIM subscription,
  with prompt estimation and remaining/consumed token response headers.
- `llm-emit-token-metric` emits the `pwwdemo` namespace with Subscription ID,
  API ID, and Agent Name dimensions.

Subscription ID is the authoritative consumer counter key. Agent Name comes
from caller-supplied `x-agent-name` and is not an authenticated agent identity.
The configured model deployment is selected by the request path.

## CLI behavior

[gateway_demo.py](../scripts/demo/gateway_demo.py) loads `APIM_GATEWAY_URL`,
`APIM_KEY_ASSET_AGENT`, `APIM_KEY_PARTNER_APP`, `APIM_API_VERSION`, and
`APIM_DEPLOYMENT_NAME` from `.env`. It supports:

| Option | Behavior |
| --- | --- |
| `--consumer asset-agent` or `partner-app` | Selects the subscription key and `x-agent-name` value |
| `--question` / `-q` | Supplies the user message |
| `--burst N` | Issues N sequential requests without an explicit inter-request delay |
| `--jailbreak` | Sends the fixed synthetic prompt-injection test once, overriding the question and burst |
| `--max-tokens` | Sets `max_completion_tokens`; defaults to 400 |

Each result row reports HTTP status, prompt/completion/total tokens, remaining
tokens, and latency. HTTP 429 includes the retry interval; recognized content
filters receive a blocked label. The burst requests consume model capacity;
their count alone does not guarantee a 429 because usage and token-bucket
replenishment affect the limit.

[warmup.sh](../scripts/demo/warmup.sh) sends three Pattern B questions, three
gateway requests per consumer, a 15-request partner-app burst, and one jailbreak
through each of the gateway and Pattern B paths. It prints UTC timestamps and
continues after individual command failures; its final message is not an
aggregate success assertion.

## Telemetry and limits of the demo

[gateway_queries.kql](../scripts/demo/gateway_queries.kql) contains Application
Insights token-metric queries and resource-specific Log Analytics queries for
gateway requests, 429s, and LLM logs. The add-on configures an Application
Insights logger/API diagnostic and a diagnostic setting to the existing
workspace. Log-table availability depends on emitted data and ingestion.

The scripts demonstrate request routing, status handling, and per-consumer
metrics. They do not configure tenant security plans, Purview policies,
Foundry guardrails, or the Foundry portal's AI Gateway association.

A content-filter block is not proof of a Defender alert. An account-level
Defender alert is not proof of an Agent 365 risk signal. Agent telemetry
ownership and the read-only diagnostic are described in
[Agent365Observability.md](Agent365Observability.md).
