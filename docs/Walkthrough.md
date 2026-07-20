# Walkthrough — Ask HR Policy Knowledge Agent

A single, linear walkthrough from a clean clone to answering an HR
question through Copilot Studio. Replaces the older "Option A vs
Option B" fork.

> **Pick a pattern first.** This walkthrough provisions the index
> needed for **Pattern A** (default — Copilot Studio queries the Azure
> AI Search Knowledge Base directly). Steps 4 and 5 are **optional**
> and only required when you upgrade to Pattern B (Foundry Agent
> Service prompt agent), Pattern C (dual-tool routing), or run the
> Hosted Agent runtime. See [RetrievalPatterns.md](RetrievalPatterns.md)
> for the decision tree.

---

## 1. Prerequisites

- Azure subscription with **AI Search**, **AI Foundry**, **OpenAI**, and
  **Document Intelligence**.
- Azure CLI (`az login`) targeting the right subscription.
- Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).
- Node.js 18+ (only if you run the React frontends).
- Copilot Studio licence (Power Virtual Agents) for Patterns A / B / C.

## 2. Clone and configure

```bash
git clone https://github.com/honestypugh2/foundry-copilot-hr-policy-knowledge.git
cd foundry-copilot-hr-policy-knowledge
uv sync
cp .env.example .env
# Edit .env — see "Required environment variables" below
```

### Required environment variables

| Variable                            | Purpose                                                          |
| ----------------------------------- | ---------------------------------------------------------------- |
| `AZURE_AI_PROJECT_ENDPOINT`         | Foundry project endpoint (`https://<proj>.services.ai.azure.com/api/projects/<proj>`) |
| `AZURE_SEARCH_ENDPOINT`             | Search service endpoint (`https://<srv>.search.windows.net`)     |
| `AZURE_OPENAI_ENDPOINT`             | OpenAI / model endpoint                                          |
| `AZURE_OPENAI_DEPLOYMENT_NAME`      | Default `gpt-5-mini` (GPT-4o retired for generative orchestration Oct 2025; override with GPT-4.1, GPT-5, or Claude where they have capacity) |
| `AGENT_SERVICE`                     | `agent-framework` (default; Hosted Agent or no agent for Pattern A) or `foundry` (Pattern B) |
| `ORCHESTRATOR_PATTERN`              | `A` (default) / `B` / `C` — selects the `/api/chat` backend path (read in `src/backend/main.py`) |
| `SEARCH_MODE`                       | `integrated_vectorization` (default) or `legacy`. `legacy` uses `HRPolicySearchService`, which has its **own** index schema (build it via `src/indexing/reindex.py`) — not the integrated-vectorization index. |

## 3. Index the knowledge base

Integrated Vectorization is the default. It runs the indexer + skillset
pipeline server-side (chunking and embedding happen in Azure AI Search).

```bash
uv run python scripts/index_knowledge_base_integrated_vectorization.py
```

> Option 2 attaches the AI Services account to the skillset via the Search
> service's managed identity (needed to enrich more than 20 documents per run).
> `azd up` grants the required **Cognitive Services User** role automatically; if
> you provisioned manually, assign it to the Search identity first.

Alternative — client-side chunking (useful for dev/test or bespoke
preprocessing):

```bash
uv run python scripts/index_knowledge_base_docintel_chunking.py
```

Local-only extraction (no Azure upload):

```bash
uv run python scripts/index_knowledge_base_docintel_chunking.py --local-only
```

See [DataPipelineAndTesting.md](DataPipelineAndTesting.md) for the full
pipeline diagram and the list of Azure resources each option creates.

## 4. (Optional) Provision the Foundry Prompt Agent (Pattern B)

Skip this step if you're starting with Pattern A. Run it when you want
force-grounded answer synthesis via `tool_choice="required"`.

```bash
# Preview what will be created (no RBAC needed — read-only)
uv run python -m src.agents.create_foundry_agent --dry-run

# Create the resources
uv run python -m src.agents.create_foundry_agent
```

Creates: **Knowledge Source → Knowledge Base → MCP connection →
PromptAgent** (`HRPolicyAgent`, `gpt-5-mini`, `tool_choice="required"`).

Verify or clean up:

```bash
uv run python -m src.agents.create_foundry_agent --verify-only
uv run python -m src.agents.create_foundry_agent --cleanup
```

See [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md) for the
agent's internal structure.

## 5. Run the FastAPI backend

```bash
uv run python -m src.backend.main
# http://localhost:8000  (OpenAPI docs at /docs)
```

Two endpoints carry most of the load:

| Endpoint           | Pattern | Latency  | Purpose                                |
| ------------------ | ------- | -------- | -------------------------------------- |
| `POST /api/chat`   | B       | ~10–14 s | Synthesised answer with citations      |
| `POST /api/lookup` | C       | ~1–2 s   | Document locator only (no LLM, no MCP) |

## 6. (Optional) Run a React frontend

```bash
# Pure Agent Framework UI
cd src/frontend && npm install && npm run dev          # http://localhost:5173
```

## 7. Wire up Copilot Studio

| If you want…                              | Follow                                                                |
| ----------------------------------------- | --------------------------------------------------------------------- |
| Copilot to call the prompt agent (B)      | [CopilotStudioIntegration.md](CopilotStudioIntegration.md) — Path 2   |
| Copilot to query the KB directly (A)      | [CopilotStudioIntegration.md](CopilotStudioIntegration.md) — Path 1   |
| Fast doc-locator routing (C)              | [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md)        |
| All three combined (hybrid)                | [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md)        |

Custom-connector OpenAPI specs:

- `copilot/openapi-v2.json` — Pattern B (`askHRPolicy`)
- `copilot/openapi-lookup-v2.json` — Pattern C (`lookupHRPolicyDocument`)
- `copilot/quick_reference_guide.md` — HR glossary + policy-number map
  (paste into the copilot's generative AI instructions or attach as a
  knowledge file).

## 8. (Optional) Run the Hosted Agent runtime

A self-contained Microsoft Agent Framework hosting container.

```bash
cd src/hosted_agent
uv run python server.py            # http://localhost:8088
docker build -t hr-policy-hosted-agent .
```

Reference: [Step 6: Host Your Agent](https://learn.microsoft.com/en-us/agent-framework/get-started/hosting?pivots=programming-language-python).

## 9. Run the test suite

```bash
uv run pytest tests/ -v
uv run pytest tests/ -v -m mock     # tests that don't need Azure
```

## 10. Deploy infrastructure

```bash
az deployment group create \
  --resource-group <your-rg> \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

---

## Troubleshooting Quick Hits

| Symptom                                          | Fix                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------- |
| `403` from Foundry on agent creation             | Grant the project's managed identity `Search Index Data Reader`      |
| `/api/chat` returns the local-search fallback    | `AZURE_AI_PROJECT_ENDPOINT` empty — set it in `.env` and restart     |
| `/api/lookup` returns 0 documents                 | Index isn't populated — re-run step 3                                |
| Copilot Studio doesn't call the right tool        | Tighten Action descriptions ([Lever 1](CopilotStudioIntegration.md)) |
| Knowledge Base MCP errors with `404`              | KB MCP API version mismatch — check `agentic_retrieval.mcp.api_version` in `src/config/search_config.json` |
