# Build the Retrieval Patterns

Use this folder to build and validate one pattern at a time. Start with Pattern
A unless you already know that its answer and citation behavior cannot meet the
scenario.

These guides preserve the five-pattern decision model from
[Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337).
Current product labels, harness requirements, and connection screens are kept in
the setup steps, but they don't create or rename architecture patterns.

Alignment was verified against blog version 1.0, updated July 21, 2026.

## Blog alignment contract

| Blog pattern | Meaning retained by these guides |
| --- | --- |
| **A** | Copilot Studio uses classic retrieval over `hr-policy-index`; no repository-owned agent runs in the answer path. |
| **A2** | Copilot Studio connects directly to `hr-knowledge-base` for agentic retrieval; no Foundry PromptAgent sits between them. |
| **B** | Foundry Agent Service runs `HRPolicyAgent`, and `tool_choice="required"` forces knowledge-base MCP retrieval before synthesis. |
| **C** | Copilot Studio routes locator turns to deterministic `/api/lookup`; answer turns can route to A, A2, or B. |
| **Hosted** | Agent Framework runs the request loop in the repository's container and supports classic or agentic retrieval. |

The shared asset layering is unchanged:

```text
hr-policy-index -> A, C, Hosted (classic modes)
   |
   +-> hr-knowledge-base -> A2, B, Hosted (agentic mode)
```

## Build order

| Order | Pattern | Build it when | Guide |
| --- | --- | --- | --- |
| 1 | **A: Direct index** | Copilot Studio should answer from Azure AI Search with native citations. | [Build Pattern A](pattern-a-direct-index.md) |
| 2 | **A2: Direct Foundry IQ** | Pattern A works, but retrieval needs agentic query planning without a separate answer agent. | [Build Pattern A2](pattern-a2-foundry-iq.md) |
| 3 | **B: Foundry agent** | Foundry must force retrieval and own answer synthesis. | [Build Pattern B](pattern-b-foundry-agent.md) |
| 4 | **C: Document locator** | Users need the exact authoritative document URL rather than a synthesized answer. | [Build Pattern C](pattern-c-document-locator.md) |
| 5 | **Hosted: Agent Framework** | You must own the runtime, middleware, authentication, or request loop. | [Build the Hosted Agent](pattern-hosted-agent.md) |

The order is a decision path, not a requirement to deploy every pattern. After
each guide's validation step, either stop with that pattern or continue only
when the next pattern solves a specific unmet requirement.

## Shared foundation

All patterns reuse `hr-policy-index`. Complete these steps once:

1. Follow [Walkthrough sections 1-3](../Walkthrough.md#1-prerequisites) to
   configure the environment and populate the index.
2. Run the shared tests:

   ```bash
   source .venv/bin/activate
   pytest -q
   ```

3. Open the guide for the pattern you want to build.

## Do not combine patterns during initial validation

Create a separate Copilot Studio test agent for each pattern. Add only the
knowledge source, tool, or external agent named in that pattern's guide. This
prevents orchestration from silently choosing a different retrieval path.

After isolated validation, use
[CopilotStudioHybridExample.md](../CopilotStudioHybridExample.md) when a single
agent genuinely needs more than one route.