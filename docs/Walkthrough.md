# Walkthrough — Ask HR Policy Knowledge Agent

A single, linear walkthrough from a clean clone to answering an HR
question through Copilot Studio. Replaces the older "Option A vs
Option B" fork.

> For pattern selection, exact file ownership, smoke tests, and benchmark entry
> points, use the authoritative
> [Pattern Setup, Code Ownership, and Benchmark Guide](PatternSetupAndBenchmarkGuide.md).

> **Pick a pattern first.** This walkthrough provisions the index
> needed for **Pattern A** (default — Copilot Studio queries the Azure
> AI Search index directly). Steps 4 and 5 are **optional**
> and only required when you upgrade to A2/B (Foundry IQ/Agent
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

## 3. Provision Azure resources (do this before indexing)

Indexing writes into an Azure AI Search service, an AI Services/OpenAI account,
and a storage account that must already exist. Provision them first with the
Azure Developer CLI from the repo root:

```bash
azd auth login
azd env new hr-demo          # or select an existing env
azd provision                # creates Search, Foundry project, storage, ACR,
                             # Container Apps env, App Insights, Grafana, and
                             # assigns the RBAC roles listed in infra/README.md
```

`azd provision` stands up infrastructure only (no app code push); use `azd up`
if you also want to build and deploy the backend container in the same step.
After it completes, copy the emitted endpoints into `.env` (the variables in the
table above) and run the identity preflight before any further Azure call:

```bash
source .venv/bin/activate
python -m src.config.azure_identity   # must exit 0 before continuing
```

Section 11 covers the full infrastructure/RBAC detail and the manual
provisioning path; you only need `azd provision` here to unblock indexing.

## 4. Index the knowledge base

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

## 5. (Optional) Provision Foundry IQ and PromptAgent resources (A2/B)

Skip this step if you're starting with Pattern A. Run it for A2's direct Foundry
IQ connection or B's force-grounded synthesis via `tool_choice="required"`.

```bash
# Preview what will be created (no RBAC needed — read-only)
uv run python -m src.agents.create_foundry_agent --dry-run

# Create the resources
uv run python -m src.agents.create_foundry_agent
```

Creates: **Knowledge Source → Knowledge Base → MCP connection →
PromptAgent** (`HRPolicyAgent`, `gpt-5-mini`, `tool_choice="required"`).
Pattern A2 uses the Knowledge Base and does not invoke the PromptAgent.

Verify or clean up:

```bash
uv run python -m src.agents.create_foundry_agent --verify-only
uv run python -m src.agents.create_foundry_agent --cleanup
```

See [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md) for the
agent's internal structure.

## 6. Run the FastAPI backend

```bash
uv run python -m src.backend.main
# http://localhost:8000  (OpenAPI docs at /docs)
```

Two endpoints carry most of the load:

| Endpoint           | Pattern | Illustrative latency | Purpose                                |
| ------------------ | ------- | -------- | -------------------------------------- |
| `POST /api/chat`   | B       | ~10–14 s | Synthesised answer with citations      |
| `POST /api/lookup` | C       | ~1–2 s   | Document locator only (no backend model, no MCP) |

These latency figures are illustrative and environment-dependent, not
benchmark results.

## 7. (Optional) Run a React frontend

```bash
# Pure Agent Framework UI
cd src/frontend && npm install && npm run dev          # http://localhost:5173
```

## 8. Wire up Copilot Studio

Build and validate one Copilot Studio pattern at a time using
[Build the Retrieval Patterns](patterns/README.md):

1. [Pattern A and its Search/SharePoint options](patterns/pattern-a-direct-index.md)
2. [Pattern A2: direct Foundry IQ](patterns/pattern-a2-foundry-iq.md)
3. [Pattern B: external Foundry agent](patterns/pattern-b-foundry-agent.md)
4. [Pattern C: deterministic document locator](patterns/pattern-c-document-locator.md)
5. [Hosted Agent](patterns/pattern-hosted-agent.md)

Stop as soon as a pattern meets the scenario. After wiring it, use the
corpus-grounded [sample query catalog](CopilotStudioTestingGuide.md#starter-query-catalog).
Combine routes only after they pass independently; see
[CopilotStudioHybridExample.md](CopilotStudioHybridExample.md).

Custom-connector OpenAPI specs:

- `copilot/openapi-v2.json` — Pattern B (`askHRPolicy`)
- `copilot/openapi-lookup-v2.json` — Pattern C (`lookupHRPolicyDocument`)
- `copilot/quick_reference_guide.md` — HR glossary + policy-number map
  (paste into the copilot's generative AI instructions or attach as a
  knowledge file).

## 9. (Optional) Run the Hosted Agent runtime

A self-contained Microsoft Agent Framework hosting container.

```bash
cd src/hosted_agent
uv run python server.py            # http://localhost:8088
docker build -t hr-policy-hosted-agent .
```

Reference: [Step 6: Host Your Agent](https://learn.microsoft.com/en-us/agent-framework/get-started/hosting?pivots=programming-language-python).

## 10. Run the test suite

```bash
uv run pytest tests/ -v
uv run pytest tests/ -v -m mock     # tests that don't need Azure
```

## 11. Deploy infrastructure

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
| `/api/lookup` returns 0 documents                 | Index isn't populated — re-run step 4                                |
| Copilot Studio doesn't call the right tool        | Tighten Action descriptions ([Lever 1](CopilotStudioIntegration.md)) |
| Knowledge Base MCP errors with `404`              | KB MCP API version mismatch — check `agentic_retrieval.mcp.api_version` in `src/config/search_config.json` |
