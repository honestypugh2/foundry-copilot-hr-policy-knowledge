# Pattern B: External Microsoft Foundry Agent

## Outcome

`HRPolicyAgent` owns answer synthesis and must call
`knowledge_base_retrieve` before answering. Copilot Studio can use it as an
external sub-agent.

## Choose an option

The blog defines Pattern B by its managed Foundry runtime and required MCP
retrieval. B1 and B2 below are current front-door options for reaching that same
Pattern B agent; they are not additional retrieval patterns.

### Option B1: Connect as an external agent

Recommended when Copilot Studio is the front door. This option requires a
**standard-harness** Copilot Studio agent.

### Option B2: Import the backend REST API

Use this only when the repository backend is already deployed and the external
agent feature is unavailable. Copilot Studio calls `/api/chat` through
`copilot/openapi-v2.json`.

## Prerequisites

- `hr-policy-index` is populated.
- `AZURE_AI_PROJECT_ENDPOINT` targets the new Microsoft Foundry portal project.
- The `HRPolicyAgent` identity can read the Search index and knowledge base.
- Option B1 uses a separate standard-harness Copilot Studio agent.
- Option B1 requires the agent endpoint's **Activity protocol**. New agents use
  the Responses protocol until published to Teams and Microsoft 365 Copilot.

## Provision and verify

```bash
source .venv/bin/activate
python -m src.agents.create_foundry_agent --dry-run
python -m src.agents.create_foundry_agent
python -m src.agents.create_foundry_agent --verify-only
```

This creates:

```text
hr-knowledge-source -> hr-knowledge-base
                    -> hr-knowledge-mcp-connection -> HRPolicyAgent
```

## Build Option B1

1. In the Microsoft Foundry portal, open `HRPolicyAgent`, select **Publish ->
  Teams and Microsoft 365 Copilot**, and complete the publish flow. Choose
  **Just you** for an isolated test. This enables the Activity protocol used
  by Copilot Studio.
2. Confirm the endpoint includes **Activity**. New-model Foundry agents can
  expose multiple protocols, so Responses may remain enabled alongside it.
3. In a standard-harness Copilot Studio agent, open **Agents -> Add an agent**.
4. Select **Connect to an external agent -> Microsoft Foundry**.
5. Create/select the connection using `AZURE_AI_PROJECT_ENDPOINT`.
6. Enter:

   | Field | Value |
   | --- | --- |
   | **Name** | `HRPolicyAgentB` |
   | **Agent Id** | `HRPolicyAgent` |
   | **Description** | Use the routing description in the detailed guide linked below. |

7. Select **Add Agent**, save, and start a new test session.

Publishing requires **Foundry User** on the project and permission to create
and configure Azure Bot Service resources, such as **Azure Bot Service
Contributor Role** on the target resource group. The agent keeps its existing
unique Entra identity in the new Foundry agent model; ensure that identity has
**Search Index Data Reader** on the Search service.

If Copilot Studio reports `Agent HRPolicyAgent endpoint does not support
activity`, the Agent Id is valid but the endpoint still exposes Responses.
Complete step 1 and retry with the same Agent Id; don't substitute the Entra
identity GUID.

Use [Pattern B external-agent details](../CopilotStudioIntegration.md#step-6-add-the-foundry-agent-to-copilot-studio)
for the complete description and Agent ID verification command.

## Build Option B2

1. Run or deploy `src/backend/main.py` with `AGENT_SERVICE=foundry`.
2. Replace the host placeholder in `copilot/openapi-v2.json` with the deployed
   HTTPS backend host.
3. Import it through **Tools -> Add a tool -> New tool -> REST API**.
4. Configure OAuth 2.0 for an Entra-protected backend; use unauthenticated public
   ingress only for a temporary demo.

## Validate

First verify Foundry directly:

```bash
source .venv/bin/activate
python -m scripts.demo.test_pattern_b \
  -q "Compare full-time and part-time PTO and cite both policies."
```

Then ask the same question in Copilot Studio. Pass when the external agent is
invoked and the answer cites Policies 50010 and 50020. The Foundry trace must
show `knowledge_base_retrieve` before synthesis.

## Stop or continue

- **Stop with B** when managed Foundry execution and forced grounding meet the
  scenario.
- Continue to [Pattern C](pattern-c-document-locator.md) only for an exact-URL
  route.
- Continue to [Hosted](pattern-hosted-agent.md) when you must own the runtime or
  middleware.

## Deeper references

- [Foundry agent architecture](../FoundryAgentArchitecture.md)
- [Pattern B prompt contract](../CopilotStudioIntegration.md#pattern-b-prompt-contract)