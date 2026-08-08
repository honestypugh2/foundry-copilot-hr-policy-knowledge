# Hosted Pattern: Agent Framework Runtime

## Outcome

The Agent Framework request loop runs in the repository's container. Use this
pattern when managed Pattern B does not provide enough control over middleware,
authentication, sidecars, or request processing.

## Choose an option

### Option H1: Local runtime

Run the hosted server locally for development and protocol validation.

### Option H2: Foundry-hosted container

Build and deploy `src/hosted_agent/`, then connect the deployed agent to
Copilot Studio.

### Retrieval mode

| `RETRIEVAL_MODE` | Strategy | Retrieval type |
| --- | --- | --- |
| `tool` (default) | `search_hr_policies` queries `hr-policy-index` | Classic hybrid and semantic Search |
| `context-semantic` | `AzureAISearchContextProvider` queries `hr-policy-index` before each model call | Classic Search |
| `context-agentic` | `AzureAISearchContextProvider` queries `hr-knowledge-base` before each model call | Agentic retrieval |

Choose one mode for the initial test and record it with the result.

## Prerequisites

- Shared infrastructure and `hr-policy-index` are ready.
- Docker is available for deployment.
- The deployment identity has the required Foundry project and Search roles.
- Copilot Studio uses a supported connection to the deployed agent or its HTTPS
  endpoint.

## Build and validate H1

```bash
source .venv/bin/activate
python -m scripts.demo.test_pattern_hosted

cd src/hosted_agent
python server.py
```

## Build H2

1. Review `src/hosted_agent/agent.yaml` and required environment variables.
2. From the repository root, deploy the `azure.ai.agent` service with the
   repository's azd workflow.
3. Confirm the deployed agent is running in Microsoft Foundry.
4. Add the deployed agent to Copilot Studio using the
   [Hosted Agent wiring](../CopilotStudioIntegration.md#hosted-agent-wiring--self-hosted-container-as-a-tool).
5. Save and start a new test session.

## Validate

Ask:

```text
Which IT policies govern employee devices, acceptable use, and information security?
```

Pass when the answer cites Policies 70070, 70010, and 70020. For `tool`, the
trace must show `search_hr_policies` before synthesis. For `context-semantic`
and `context-agentic`, verify the context provider retrieved evidence before the
model call; those modes don't require a tool invocation.

## Stop or combine

- **Stop with Hosted** when runtime ownership is the requirement and the route
  passes security, reliability, and answer-quality checks.
- Add Pattern C only if users also need an exact document locator.
- Do not run Hosted and Pattern B for the same intent without an explicit router.

## Deeper references

- [Managed versus hosted architecture](../AgentArchitecturePaths.md)
- [Hosted prompt contract](../CopilotStudioIntegration.md#hosted-prompt-contract)
- [Deployment configuration](../../src/hosted_agent/agent.yaml)