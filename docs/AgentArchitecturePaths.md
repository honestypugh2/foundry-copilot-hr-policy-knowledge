# Agent Architecture Paths

This repo ships **two SDK paths** for the same HR policy agent. Choose
one based on **where the agent runs** and **who orchestrates the tools**.

| Decision factor                   | Foundry Agent Service (Pattern B, default ★) | Microsoft Agent Framework (Hosted Agent runtime) |
| --------------------------------- | -------------------------------------------- | ------------------------------------------------ |
| **Runtime**                       | Managed by Azure (Foundry project)           | Self-hosted container (`src/hosted_agent/`)      |
| **SDK**                           | `azure-ai-projects>=2.2.0`                   | `agent-framework>=1.8.1` + `agent-framework-foundry>=1.8.1` |
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

★ **Default in this repo.** Set `AGENT_SERVICE=foundry` (or omit — it's
the default).

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
| `foundry` (default)          | `src.agents.hr_policy_agent.HRPolicyAgent`              | Foundry Agent Service (B)      |
| `agent-framework`            | `src.agents.hr_policy_agent_af.HRPolicyAgent`           | Hosted Agent (Agent Framework) |

Both classes expose the same interface (`initialize()`,
`answer_question_async()`, `close()`), so the FastAPI backend code is
identical for both.

---

## SDK Reference Snippets

### Foundry Agent Service

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from azure.identity import DefaultAzureCredential

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
project.agents.create_version(
    agent_name="HRPolicyAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions=AGENT_INSTRUCTIONS,
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
    model="gpt-4o",
    credential=DefaultAzureCredential(),
)
agent = chat_client.as_agent(
    name="HRPolicyAgent",
    instructions=HR_POLICY_SYSTEM_PROMPT,
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
