# Agent 365 observability

This repository has two Foundry agent runtimes with different telemetry owners:

| Runtime | Code | Activity collection |
| --- | --- | --- |
| Managed prompt agent (`HRPolicyAgent`, Pattern B) | [hr_policy_agent.py](../src/agents/hr_policy_agent.py) | Foundry service-side collection |
| Hosted agent (`hr-policy-agent`) | [server.py](../src/hosted_agent/server.py) | Foundry hosting SDK with Microsoft OpenTelemetry |

Registry synchronization, activity collection, and security-risk attribution are
separate pipelines. Publication supplies agent inventory; it does not prove that
activity has been ingested or that a Defender alert is attributed to that agent.

## Hosted telemetry ownership

`ResponsesHostServer` initializes the hosted OpenTelemetry provider through
`agent-framework-foundry-hosting` and `azure-ai-agentserver-core`. The hosting
SDK configures Microsoft OpenTelemetry, including Foundry identity enrichment
and Agent 365 export in supported hosted environments.

The repository explicitly declares `microsoft-opentelemetry>=1.3.5,<2` in both
[pyproject.toml](../pyproject.toml) and the standalone hosted
[requirements.txt](../src/hosted_agent/requirements.txt). Microsoft OpenTelemetry
is the supported path for new integrations, replacing the deprecated
`microsoft-agents-a365-observability-*` packages.

[server.py](../src/hosted_agent/server.py) passes
`APPLICATIONINSIGHTS_CONNECTION_STRING` to `ResponsesHostServer` when present.
Azure Monitor and Agent 365 are separate export destinations; an Application
Insights connection string is not an Agent 365 connection string.

The hosted entry point does not call
[src.observability.enable_tracing](../src/observability/tracing.py). That module
belongs to the repository's backend/client tracing path and is not packaged in
the standalone hosted image. Initializing it before the hosting SDK can also
create competing OpenTelemetry provider configurations.

## Runtime configuration contract

| Configuration | Owner | Meaning |
| --- | --- | --- |
| `a365LoggingEnabled` | Foundry account | Collection setting inherited by projects and prompt agents; also controls native hosted collection for new sessions |
| `a365Status` | Foundry service | Effective status after licensing and consent checks |
| `FOUNDRY_HOSTING_ENVIRONMENT` | Hosted platform | Identifies the hosted environment |
| `FOUNDRY_AGENT365_TRACING_ENABLED` | Hosted platform | Enables the native Agent 365 export path |
| `FOUNDRY_AGENT_INSTANCE_CLIENT_ID` | Hosted platform | Agent instance identity used for telemetry attribution |
| `FOUNDRY_AGENT_TENANT_ID` | Hosted platform | Tenant context for the agent |
| `FOUNDRY_AGENT_BLUEPRINT_CLIENT_ID` | Hosted platform | Blueprint identity context |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application environment | Optional Azure Monitor export destination |

Platform identity values are runtime context, not application-generated IDs.
The agent identity, blueprint identity, and project managed identity are distinct.
The hosted code relies on the hosting SDK's platform configuration rather than
forcing Agent 365 export on in local processes.

The Foundry integration requires the applicable Agent 365 licensing and tenant
consent, account collection enabled, and outbound HTTPS connectivity to
`agent365.svc.cloud.microsoft`. The Foundry hosted-permissions guide specifies
the `Agent365.Observability.OtelWrite` app role on `Agent365Observability` for
the hosted Entra Agent Identity. Graph app-role assignments use the principal's
object ID. These are external service prerequisites, not permissions granted by
the agent application or its preflight.

## Prompt-agent collection

Pattern B creates or uses a managed `PromptAgentDefinition` and invokes the
Foundry Responses API with an agent reference. Foundry owns its runtime
instrumentation and account-level collection. A caller-side SDK does not
instrument the managed prompt-agent runtime.

The direct model route in [gateway_demo.py](../scripts/demo/gateway_demo.py) is
not a published-agent invocation. Its `x-agent-name` header supplies an APIM
metric dimension, not an authenticated Entra Agent Identity.

## Privacy and logging

The native hosting SDK defaults to sensitive-content recording disabled.
The hosted search tool logs whether glossary expansion occurred, not the raw
question or expanded search query. Application logs can be exported by the
hosting SDK, so raw query logging would bypass span-content privacy controls.
The backend/client tracing implementation is unchanged.

## Read-only configuration diagnostic

[agent365_preflight.py](../scripts/demo/agent365_preflight.py) reads Azure
Resource Manager, Microsoft Graph, and Defender pricing configuration through
the Azure CLI. It sends no prompts and performs no permission or policy writes.

Example CLI shape:

```text
python -m scripts.demo.agent365_preflight \
  --account-resource-id <foundry-account-arm-id> \
  --hosted-agent-principal-id <agent-identity-object-id>
```

`--account-resource-id` defaults to the parent account of
`AZURE_AI_PROJECT_RESOURCE_ID` loaded from the repository's ignored `.env`.
`--hosted-agent-principal-id` is repeatable; coverage is limited to explicitly
supplied identities. The diagnostic does not discover all tenant agents.

The diagnostic checks:

- Active subscription against the target account and, when configured,
  `EXPECTED_AZURE_SUBSCRIPTION_ID` and `EXPECTED_AZURE_TENANT_ID`.
- Account collection enabled and effective status `Enabled`, using ARM API
  `2026-03-15-preview`.
- Exactly one `Agent365Observability` service principal with the enabled
  OtelWrite role.
- The exact role/resource assignment for each supplied hosted principal.
- Defender AI pricing tier and the `AIPromptEvidence` extension separately.

Each result contains a name, `PASS`/`FAIL`/`UNKNOWN` status, and detail. Azure CLI
failures surface their error output instead of becoming successful checks.

| Exit code | Meaning |
| --- | --- |
| `1` | A configuration check or service read failed |
| `2` | No configuration failure, but coverage or end-to-end visibility is unknown; the current implementation always leaves ingestion unknown |
| `0` | Reserved by the aggregate status logic for a result with neither failures nor unknowns; not currently emitted after successful collection |

Configuration reads cannot prove successful ingestion or alert backfill.

## Security-signal boundaries

A refusal, an HTTP 400 content-filter response, a Defender alert, and an Agent
365 risk signal are distinct results. The SDK does not manufacture security
alerts from spans or import arbitrary account-level alerts into Agent 365.

Agent 365 aggregates active, agent-attributed risk signals from the connected
security platforms. Risk counts can lag those platforms by up to one hour.
An account-level Foundry detection or a `defender_for_ai` result with
`evaluation=unavailable` does not establish agent-level detection or ingestion.
The repository's automated checks do not verify Agent 365 UI activity or risk
arrival, and enabling collection does not guarantee historical alert backfill.

APIM MCP governance is another integration: it covers MCP inventory and tool
access enforcement, not automatic conversion of model API responses into
per-agent jailbreak alerts.

## Test coverage

[test_agent365_integration.py](../tests/test_agent365_integration.py) covers the
hosted entry point's native exporter ownership, optional Application Insights
configuration, platform-controlled Agent 365 export, query-log privacy,
read-only preflight requests, and configuration failures. The tests mock service
calls and do not establish remote telemetry ingestion.

[test_observability_tracing.py](../tests/test_observability_tracing.py) covers
the separate backend/client tracing implementation.

## References

- [Foundry integration and agent types](https://learn.microsoft.com/azure/foundry/agents/concepts/agent-365-integration)
- [Foundry hosted observability permissions](https://learn.microsoft.com/azure/foundry/agents/how-to/grant-agent-365-permissions)
- [Foundry collection settings](https://learn.microsoft.com/azure/foundry/agents/how-to/configure-agent-365-data-collection)
- [Microsoft OpenTelemetry Distro](https://learn.microsoft.com/microsoft-agent-365/developer/microsoft-opentelemetry)
- [Agent 365 risk-signal semantics](https://learn.microsoft.com/microsoft-agent-365/admin/agent-registry-overview#agent-risks)
- [APIM MCP governance](https://learn.microsoft.com/azure/api-management/agent-365)
