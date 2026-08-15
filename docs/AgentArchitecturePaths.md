# Agent Architecture Paths

This repo ships **two SDK paths** for the same HR policy agent. Choose
one based on **where the agent runs** and **who orchestrates the tools**.

| Decision factor                   | Foundry Agent Service (Pattern B)            | Microsoft Agent Framework (Hosted Agent runtime, default ★) |
| --------------------------------- | -------------------------------------------- | ------------------------------------------------ |
| **Runtime**                       | Managed by Azure (Foundry project)           | Self-hosted container (`src/hosted_agent/`)      |
| **SDK**                           | `azure-ai-projects>=2.3.0`                   | `agent-framework>=1.11.0` + `agent-framework-foundry>=1.10.1` |
| **Agent definition**              | `PromptAgentDefinition` published to the project | `Agent` instance in process                  |
| **Tool location**                 | Server-side (MCPTool inside the agent)        | Client-side (`@tool` Python functions)          |
| **Provisioning command**          | `python -m src.agents.create_foundry_agent`  | `cd src/hosted_agent && uv run python server.py` |
| **Code path**                     | `src/agents/hr_policy_agent.py`              | `src/agents/hr_policy_agent_af.py`              |
| **Search backend**                | Knowledge Base MCP endpoint                  | Direct `SearchClient` calls                      |
| **Force-grounding mechanism**     | `tool_choice="required"`                     | Tool description + system prompt                 |
| **Invocation API**                | OpenAI Responses API + `extra_body.agent_reference` | `agent.run("…")`                          |
| **Streaming**                     | OpenAI Responses streaming                   | `agent.run("…", stream=True)`                   |
| **Multi-step orchestration**      | Limited (single agent, single tool)           | Full (`SequentialBuilder`, custom Executors)     |
| **Portal visibility**             | Yes — appears in Foundry portal              | Manual: register via `AIProjectClient` (optional) |
| **Custom auth / sidecars**        | Not supported                                | Yes (you control the container)                  |
| **Deployment surface**            | Foundry project (managed)                    | App Service / Container Apps / AKS / your own infra |
| **Cost model**                    | Per-token + Foundry runtime                  | Per-token + your compute                         |
| **Foundry GA?**                   | ✅ GA                                         | ✅ GA (the *Agent Framework hosting* pattern)     |
| **Best for**                      | "Just answer the question and cite policy"   | Self-hosted runtime, custom auth, multi-step orchestration |

★ **Backend service default.** Omit `AGENT_SERVICE` or set it to
`agent-framework` to use the Agent Framework path. Set
`AGENT_SERVICE=foundry` explicitly for Pattern B. Pattern A remains the
recommended starting pattern and does not require either backend agent path.

---

## When to Pick Each

### Pick **Foundry Agent Service** when…

- You want the agent visible in the Foundry portal alongside other agents.
- You want force-grounding via `tool_choice="required"`.
- You don't need custom auth, request inspection, or sidecars.
- You're calling the agent from Copilot Studio or another OpenAI-compatible client.

### Pick **Microsoft Agent Framework hosting** when…

- You need to run multi-step workflows (`SequentialBuilder`, Executors).
- You need custom middleware (auth, logging, rate limits) inside the runtime.
- You want to keep the answering loop on your own infrastructure.
- You need to combine multiple tools that aren't easily expressed as MCP.

---

## Switching Between Paths

The orchestrator picks the path from the `AGENT_SERVICE` env var:

| `AGENT_SERVICE`              | Effective class                                         | Pattern                        |
| ---------------------------- | ------------------------------------------------------- | ------------------------------ |
| `foundry`                    | `src.agents.hr_policy_agent.HRPolicyAgent`              | Foundry Agent Service (B)      |
| `agent-framework` (default)  | `src.agents.hr_policy_agent_af.HRPolicyAgent`           | Hosted Agent (Agent Framework) |

Both classes expose the same interface (`initialize()`,
`answer_question_async()`, `close()`), so the FastAPI backend code is
identical for both.

---

## `orchestrator.py` vs. the pattern agents (benchmark boundary)

`src/agents/orchestrator.py` (`HRPolicyWorkflowOrchestrator`) is a **different
architecture** from the pattern agents, and the benchmark deliberately does
**not** use it:

| | `hr_policy_agent_af.py` (Hosted) | `orchestrator.py` |
| --- | --- | --- |
| Shape | Single Agent Framework agent (autonomous `@tool` or context provider) | `SequentialBuilder` pipeline of custom Executors |
| View | **Black box** — one end-to-end answer + citations + usage | **White box** — inspectable per-phase state (query understanding → retrieval → synthesis) |
| Used by | The **benchmark** (measures each pattern in isolation) and `/api/chat` | Only the backend `/api/chat` workflow; its `AGENT_SERVICE` switch is a *fallback* |

**What orchestrator gives you:** phase-level observability (query planning,
retrieval, grounding, synthesis as separate steps). Benchmarking through it
would collapse pattern isolation, so it is not a benchmark target.

**You do not lose the agentic-retrieval phases in the benchmark.** The Knowledge
Base query-planning trace (`modelQueryPlanning` → sub-queries → `agenticReasoning`)
is captured directly by Pattern A2 and, via the tracing context provider, by the
Hosted `context-agentic` agent. It is summarized per run and shown in the
workbench **Experiment detail → Agentic retrieval phases** table.

---

## Hosted retrieval modes, prompts, and which evaluation lane grades them

The Hosted pattern runs in one of three `RETRIEVAL_MODE` values. **The mode
selects both the retrieval mechanism and the system prompt** — keep them paired
or the agent is told to use a tool that isn't registered.

| `RETRIEVAL_MODE` | Retrieval mechanism | System prompt (must match) |
| --- | --- | --- |
| `tool` (default) | Classic `search_hr_policies` `@tool` (hybrid search) | tool prompt — *"You MUST call `search_hr_policies` first"* |
| `context-semantic` | `AzureAISearchContextProvider`, classic search, injected before each turn | context prompt — *"answer using ONLY the provided context"* |
| `context-agentic` | `AzureAISearchContextProvider`, agentic KB retrieval (query planning + sub-queries) | context prompt (same as above) |

Both Hosted code paths implement this pairing:

- Benchmark agent [`src/agents/hr_policy_agent_af.py`](../src/agents/hr_policy_agent_af.py) —
  `HR_POLICY_SYSTEM_PROMPT` (tool) / `HR_POLICY_CONTEXT_SYSTEM_PROMPT` (context modes).
- Deployed runtime [`src/hosted_agent/server.py`](../src/hosted_agent/server.py) —
  `HR_POLICY_INSTRUCTIONS` (tool) / `HR_POLICY_CONTEXT_INSTRUCTIONS` (context modes).

> ⚠️ The **deployed** Hosted agent (`hr-policy-agent`) inherits its mode from the
> azd env var `RETRIEVAL_MODE` (see [`azure.yaml`](../azure.yaml)). If it is unset
> the deployed agent runs in **`tool`** mode. To benchmark/evaluate the
> `context-agentic` variant at the deployed boundary, deploy with
> `RETRIEVAL_MODE=context-agentic` before running the evaluation.

### Which evaluation lane grades each pattern

Quality is graded where the pattern's **real runtime** lives, so the score
reflects the actual answer engine rather than a routing shell:

| Pattern | Real runtime | Quality lane |
| --- | --- | --- |
| A (Direct KB) | Copilot Studio + AI Search | **Copilot Studio native evaluation** (standard harness) |
| A2 | Copilot Studio (GitHub Copilot harness) | **Copilot Studio native evaluation** (GitHub Copilot harness — different CSV template) |
| C (Dual-tool routing) | Copilot Studio router + AI Search | **Copilot Studio native evaluation** (standard harness) |
| B (Foundry prompt agent) | Foundry Agent Service `HRPolicyAgent` | **Foundry portal evaluation** / deployed-agent replay evaluator |
| Hosted | Foundry hosted agent `hr-policy-agent` | **Foundry portal evaluation** / deployed-agent replay evaluator |

For **B and Hosted**, grade quality at the Foundry boundary (Foundry portal
Automatic Evaluation, or the repo's `evaluation_attachment --foundry-hosted-agent`
replay). Their Copilot Studio front-door is a thin routing shell used only for
Direct Line latency/reliability evidence, not the quality score.

Latency/reliability across Copilot Studio front doors is a separate lane
(Direct Line benchmark) and does not populate the native Evaluation page — see
[CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md).

### Model parity and confounds

The answer model is **not uniform** across patterns, and in some patterns you
cannot make it uniform:

| Where | Answer model | Control |
| --- | --- | --- |
| Foundry patterns — B, Hosted (tool / context-semantic / context-agentic) | `gpt-5-mini` (also the context-agentic sub-query planning model) | You pin it (`AZURE_AI_MODEL_DEPLOYMENT_NAME`) |
| Copilot Studio A, C, and the B/Hosted front doors | Microsoft-managed standard-harness model (~GPT-4.1 since GPT-4o retired Oct 2025) | Selectable in the maker portal, but not token-instrumentable — bills per-message Credits, not tokens |
| Copilot Studio A2 | GitHub Copilot harness model set | Selectable in the maker portal, but not token-instrumentable — bills per-message Credits, not tokens |

Consequences for interpreting results:

- **Hold the model constant where you control it.** The Foundry Hosted retrieval
  modes all run `gpt-5-mini`, so their comparison isolates *retrieval strategy*,
  not model capability. Vary the model only as a deliberate separate axis.
- **Cross-platform quality deltas are confounded by model.** A Foundry-vs-Copilot-
  Studio quality difference mixes retrieval *and* model. Compare within a platform
  first; state the model caveat before any cross-platform quality claim. Do not
  switch Foundry to GPT-4.1 to fake parity — Copilot Studio's exact model/version
  isn't disclosed, so it would be approximate, not true parity.
- **The evaluation judge model is held constant across all patterns**, so quality
  scores remain comparable even when the answer models differ.
- **Provenance records it.** Every experiment manifest carries `answer_model`:
  `gpt-5-mini` for Foundry, `microsoft_managed_standard_harness` /
  `github_copilot_harness` for the opaque Copilot Studio lanes, and `none_*`
  for retrieval-only or deterministic options that generate no answer. When you
  select a specific model in the maker portal you may annotate the marker with
  the selection (for example `microsoft_managed_standard_harness:gpt-4.1`), but
  the marker stays the source of truth: the exact served model/version is not
  disclosed and Copilot Studio never joins Foundry's per-token cost axis because
  it is billed in per-message Credits.

---

## SDK Reference Snippets

### Foundry Agent Service

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from azure.identity import DefaultAzureCredential

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
# Provisioned by _build_prompt_agent_definition() in src/agents/create_foundry_agent.py;
# `instructions` embeds retrieval/answer guidance from src/config/search_config.json.
# Verify the live prompt in the Foundry portal: Agents -> HRPolicyAgent -> Instructions.
project.agents.create_version(
    agent_name="HRPolicyAgent",
    definition=PromptAgentDefinition(
        model="gpt-5-mini",
        instructions=instructions,
        tools=[MCPTool(
            server_label="hr-knowledge",
            server_url=KB_MCP_ENDPOINT,
            require_approval="never",
            allowed_tools=["knowledge_base_retrieve"],
            project_connection_id="hr-knowledge-mcp-connection",
        )],
        tool_choice="required",
    ),
)

openai = project.get_openai_client()
conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": "HRPolicyAgent", "type": "agent_reference"}},
    input=question,
)
print(response.output_text)
```

### Microsoft Agent Framework (Hosted Agent)

```python
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

@tool(name="search_hr_policies", description="Search HR policy KB")
def search_hr_policies(query: str) -> list[dict]:
    return search_client.search(query=query, top=5)

chat_client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model="gpt-5-mini",
    credential=DefaultAzureCredential(),
)
# Hosted-agent prompt lives in the container (src/hosted_agent/server.py):
# HR_POLICY_INSTRUCTIONS for tool mode; HR_POLICY_CONTEXT_INSTRUCTIONS for the
# context-semantic / context-agentic modes. The Foundry agent record itself
# carries no instructions (kind=hosted), so the portal shows none for it.
agent = chat_client.as_agent(
    name="HRPolicyAgent",
    instructions=HR_POLICY_INSTRUCTIONS,
    tools=[search_hr_policies],
)
result = await agent.run("How many PTO hours do I get?")
print(result.text)
```

---

## See Also

- [RetrievalPatterns.md](RetrievalPatterns.md) — overall pattern decision tree
- [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md) — Pattern B internals
- [Quickstart: Create a prompt agent](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent?tabs=python)
- [Step 6: Host Your Agent (Agent Framework)](https://learn.microsoft.com/en-us/agent-framework/get-started/hosting?pivots=programming-language-python)
