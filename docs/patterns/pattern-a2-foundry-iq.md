# Pattern A2: Copilot Studio to Foundry IQ

## Outcome

Copilot Studio owns answer synthesis while Foundry IQ retrieves from
`hr-knowledge-base`. The knowledge base plans subqueries, retrieves in parallel,
reranks, and merges evidence. There is no PromptAgent in the request path.

## Supported option

Use the native **Build -> Tools -> Foundry IQ** experience in a **GitHub Copilot
harness** agent. The **Azure - Foundry IQ** API and MCP connector actions are
not equivalent substitutes; they do not establish the native Search-service
and knowledge-base binding.

The published blog shows the earlier label **Build -> Microsoft IQ -> Foundry
IQ**. Current Microsoft Learn and the current Copilot Studio experience place
the same native Foundry IQ connection under **Build -> Tools**. This is a UI
label change, not a different retrieval pattern.

## Prerequisites

- Pattern A's shared `hr-policy-index` is populated.
- The Copilot Studio agent uses the GitHub Copilot harness.
- The tenant exposes the top-level **Foundry IQ** tool card.
- The maker can access `hr-knowledge-base` in the same Entra tenant.

Microsoft Entra ID Integrated authentication can support identity-aware,
ACL-trimmed retrieval when the underlying knowledge sources and permissions are
configured for it. Validate that separately with identities that have different
document access.

## Build

1. Provision the knowledge source and knowledge base:

   ```bash
   source .venv/bin/activate
   python -m src.agents.create_foundry_agent
   ```

   This command also creates Pattern B's `HRPolicyAgent`; A2 does not call it.

2. In Copilot Studio, open **Build -> Tools -> Foundry IQ**.
3. Create an Entra ID Integrated connection with the Search service root
   endpoint.
4. Select `hr-knowledge-base`, add it to the agent, and save.
5. Add the [A2 retrieval instructions](../CopilotStudioIntegration.md#a2-prompt-contract).
6. Start a new test session.

Use the detailed [A2 click path](../CopilotStudioIntegration.md#pattern-a2-wiring-github-copilot-harness--foundry-iq)
if the labels differ slightly in the current UI.

## Validate

Ask:

```text
Compare the uniform and non-uniform dress code policies.
```

Pass when the activity trace contains a **Foundry IQ retrieval** and the answer
uses Policies 60010 and 60020. A call to **Foundry IQ Knowledge Retrieval
(API)** or an HTTP 400 is not a passing A2 route.

## If the Foundry IQ card is missing

Pattern A2 cannot be configured through the supported UI in that environment.
Capture the environment ID and missing tool card, then raise a Microsoft support
request. Continue using Pattern A, or build Pattern B in a separate
standard-harness agent.

## Stop or continue

- **Stop with A2** when Copilot Studio synthesis plus agentic retrieval meets
  the scenario.
- Continue to [Pattern B](pattern-b-foundry-agent.md) when Foundry must enforce
  retrieval and own answer synthesis.

## Deeper references

- [A2 prompt contract and troubleshooting](../CopilotStudioIntegration.md#pattern-a2-wiring-github-copilot-harness--foundry-iq)
- [A2 test cases](../CopilotStudioTestingGuide.md#starter-query-catalog)