# Copilot Studio Integration Guide

This document describes how to connect **Copilot Studio** to the HR Policy Knowledge Agent so employees can ask HR questions directly from a Teams bot or web chat. Two integration paths are supported.

## Two Integration Paths

| Path | How It Works | Best For |
|------|-------------|----------|
| **Path 1: Knowledge Source (Direct)** | Copilot Studio queries `hr-policy-index` directly via its native Azure AI Search connector. Supports text + vector (integrated vectorization) + semantic ranker. Copilot Studio's built-in LLM synthesizes the answer. | Simple Q&A, fast responses, quick setup |
| **Path 2: Foundry Agent Action** | Copilot Studio invokes a Foundry Agent as an Action (via **Tools** → **Azure AI Foundry agent** or a **REST API tool**). The agent uses agentic retrieval (Foundry IQ) for AI-planned query routing, subquery decomposition, and source attribution with custom retrieval + answer instructions. | Complex queries, multi-source, detailed citations, grounded reasoning |

## Prerequisites

| Requirement | Details |
|---|---|
| Copilot Studio license | Power Virtual Agents / Copilot Studio |
| Power Platform environment | `` |
| Azure AI Search index | `hr-policy-index` (deployed via this project) |
| Azure AI Search API key | Reader access (query key) |
| Azure AI Foundry project | Required for Path 2 only |
| RBAC: Search Index Data Reader | Assigned to Foundry project managed identity (Path 2 only) |

## Architecture

```
Employee (Teams / Web) ──► Copilot Studio Bot
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               Path 1              Path 2
            Knowledge Source     Foundry Agent Action
            (Azure AI Search)      │
                    │              ▼
                    │         Foundry Agent (gpt-4o)
                    │              │
                    │         MCP Tool: knowledge_base_retrieve
                    │              │
                    │         Knowledge Base (Foundry IQ)
                    │              │
                    └──────┬───────┘
                           ▼
                      hr-policy-index
                           │
                           ▼
                  Grounded HR Policy Answer
```

---

## Path 1: Azure AI Search as Knowledge Source

## Step 1: Create a Copilot in Copilot Studio

1. Navigate to [Copilot Studio](https://copilotstudio.microsoft.com)
2. Click **Create** → **New copilot**
3. Name: `Ask HR Policy Agent`
4. Description: `Answers employee questions using internal HR policy documents`
5. Language: English

## Step 2: Add Azure AI Search as a Knowledge Source

1. In the copilot editor, go to the **Knowledge** page (or click **Add knowledge** from the **Overview** page)
2. Click **Add knowledge** → under **Featured**, select **Azure AI Search**
3. Click **Create new connection**
4. Select authentication type: **Access Key**
5. Enter the connection details:

| Field | Value |
|---|---|
| Azure AI Search Endpoint URL | `https://<your-search-service>.search.windows.net` |
| Azure AI Search Admin Key | Your API key (query key is sufficient for read-only) |

6. Click **Create** — a green check mark confirms the connection
7. Click **Next**
8. Enter the index name: `hr-policy-index`
9. Click **Add to agent** to complete the connection
10. Wait for the status to change from **In progress** to **Ready**

> **Semantic Ranker**: The index is provisioned with `semanticSearch: 'free'` and a semantic configuration named `hr-semantic-config` (title → `title`, content → `content`, keywords → `category`). Copilot Studio automatically leverages the semantic ranker when querying an index that has a semantic configuration.
>
> **Vector Search**: Both indexing options now configure an `AzureOpenAIVectorizer` (`text-embedding-3-small`) on the index, enabling Copilot Studio to execute **hybrid (text + vector + semantic)** search automatically — no Foundry project needed. The vectorizer uses the Azure OpenAI endpoint directly (`AZURE_OPENAI_ENDPOINT`).

## Step 3: Configure Agent Instructions and Generative AI Settings

By default, new agents use **generative orchestration**, which automatically searches all knowledge sources added on the Knowledge page. You do **not** need to modify the Conversational boosting system topic — it is not used in generative orchestration mode.

### 3a. Add Instructions (Overview page)

1. Open your agent in Copilot Studio
2. On the **Overview** page, find the **Instructions** text box
3. Enter the following instructions:

```
You are an HR policy assistant. Answer questions ONLY using the provided HR policy documents.

- Always cite the specific policy number (e.g., Policy 51350)
- If a policy doesn't cover the question, say so clearly
- Never provide legal advice
- Use professional, clear language
- Reference the exact policy title and section when possible
- Use the FAQ documents only if the question is not relevant to specific HR policies
```

These instructions guide the agent when it decides which knowledge sources to search, how to fill tool inputs, and how to generate responses.

### 3b. Configure Generative AI Settings

1. Go to **Settings** → **Generative AI**
2. Under **Orchestration**, confirm **Use generative AI orchestration** is set to **Yes** (this is the default)
3. Optionally turn off **Allow the AI to use its own general knowledge** if you want the agent to answer **only** from the HR policy index (recommended for grounded answers)
4. Set **Content moderation** to **High** (default) to filter harmful content
5. Click **Save**

> **Note — Classic orchestration**: If you need to use classic orchestration instead, go to **Topics** → **System** → **Conversational boosting** to configure the generative answers node with specific knowledge sources and a system message. However, generative orchestration is recommended for new agents.

## Step 4: Configure Vernacular Handling

Since Copilot Studio has limited prompt customization, we address vernacular through multiple layers:

1. **Index-level synonym map (`hr-glossary-synonyms`)**: The `create_index()` method in `search_service.py` creates an Azure AI Search synonym map attached to the `title`, `content`, and `category` fields. This expands informal terms **at query time** so Copilot Studio benefits even though it bypasses the Python backend:
   - "PTO", "time off", "vacation" ↔ "Paid Time Off"
   - "sick leave", "sick time", "std" ↔ "Short-Term Disability"
   - "dress code", "what to wear", "uniforms" ↔ "Uniform Dress Code"
   - _(Full glossary: 30+ mappings in `HR_GLOSSARY` dict)_

2. **Python-side glossary expansion**: The backend API also applies `expand_query_with_glossary()` before sending queries to AI Search, providing an additional layer for direct API consumers.

3. **Custom topic for common terms**: Create a topic for frequently misunderstood terms:
   - Trigger: "What does [term] mean?"
   - Action: Query the glossary endpoint `/api/glossary`

---

## Path 2: Foundry Agent Action (Agentic Retrieval)

This path gives Copilot Studio access to the Foundry Agent's agentic retrieval pipeline — AI-planned query routing, subquery decomposition, semantic ranking, answer synthesis, and custom retrieval/answer instructions — all against the same `hr-policy-index`.

> **Prerequisites from Path 1:** Before adding the tool, complete Path 1 Step 3 (Configure Agent Instructions) and Step 3b (Configure Generative AI Settings). Instructions tell the agent how to format responses and cite policy numbers; Generative AI settings enable orchestration and disable general knowledge. Path 1 Step 2 (Add Azure AI Search Knowledge Source) is optional for Path 2 — the Foundry agent runs its own retrieval pipeline.

### Step 5: Create the Foundry Agent

Run the setup script to create all Foundry IQ resources:

```bash
python scripts/create_foundry_agent.py
```

This creates:
1. **Knowledge Source** (`hr-knowledge-source`) → points to `hr-policy-index`
2. **Knowledge Base** (`hr-knowledge-base`) → wraps knowledge source(s)
3. **MCP connection** in Foundry project (managed identity)
4. **Foundry Agent** (`HRPolicyAgent`, gpt-4o) with `knowledge_base_retrieve` MCP tool

To verify all resources exist:
```bash
python scripts/create_foundry_agent.py --verify-only
```

**RBAC requirements:**

| Role | Assigned To | Purpose |
|------|-------------|---------|
| Search Index Data Contributor | Your user identity | Create indexes, upload documents |
| Search Index Data Reader | User + Project Managed Identity | Query indexes, access knowledge base |
| Search Service Contributor | Your user identity | Create knowledge bases and sources |

### Step 6: Add the Foundry Agent to Copilot Studio

**Option A — Add Foundry Agent directly:**

1. In Copilot Studio, go to **Tools** → **Add a tool** → **New tool** → **Azure AI Foundry agent**
2. Select your AI Foundry project and the `HRPolicyAgent`
3. The Foundry agent runs as a sub-agent for complex tasks with agentic retrieval
4. Under **Completion**, select **Write the response with generative AI** (lets Copilot Studio format the answer with citations)
5. Click **Save**

See: [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent)

**Option B — Add as REST API tool (if agent is deployed as an API):**

If your Foundry Agent is exposed via an Azure Function or FastAPI endpoint:

1. Go to **Tools** → **Add a tool** → **New tool** → **REST API**
2. Upload an OpenAPI spec that describes your endpoint (e.g., `POST /api/ask` or `POST /api/chat`)
3. Configure authentication (API key or managed identity)
4. Map the user's message to the `query` input parameter
5. Under **Details**, ensure **Allow agent to decide dynamically when to use the tool** is checked
6. Under **Completion**, select **Write the response with generative AI**

> **UI Note:** Copilot Studio renamed *Actions* to *Tools* (April 2025+). The steps above reflect the current UI.

### Step 7: Wire the Tool in Topics (Optional)

If you prefer explicit routing instead of generative orchestration:

1. Go to **Topics** → create or edit a topic
2. Add node (+) → **Add a tool** → select the Foundry agent tool
3. Map the user's message to the `query` input
4. Under **Completion**, author a specific response template referencing output variables

### Key Difference: Direct Search vs. Foundry Agent Pipeline

| Aspect | Path 1: Knowledge Source (Direct) | Path 2: Foundry Agent Action |
|--------|----------------------------------|------------------------------|
| **Search type** | Text + vector (integrated vectorization) + semantic ranker | Agentic retrieval (query planning + subqueries + semantic ranking + answer synthesis) |
| **Answer synthesis** | Copilot Studio built-in LLM | Foundry Agent (gpt-4o) with custom instructions |
| **Query planning** | None — single query | LLM-driven subquery decomposition |
| **Multi-source** | Single index per Knowledge Source | Multiple knowledge sources in one Knowledge Base |
| **Custom instructions** | Limited (Copilot Studio instructions field) | Full retrieval + answer instructions in `search_config.json` |
| **Source attribution** | URL-based citations (`metadata_storage_path`) | Rich per-fact source attribution with policy numbers |
| **Latency** | Lower (direct search) | Higher (agent reasoning + tool call) |
| **Complexity** | Simpler setup | Requires Foundry project + RBAC |

---

## Publish and Test

### Step 8: Publish to Teams

1. Go to **Channels** → **Microsoft Teams**
2. Click **Turn on Teams**
3. Configure:
   - Display name: `Ask HR`
   - Description: `Ask questions about HR policies`
4. Click **Publish**
5. Share the bot link with employees

## Step 9: Testing

### Test in Copilot Studio
1. Use the **Test** pane in Copilot Studio
2. Try these questions:
   - "What is the PTO policy?"
   - "How many holidays do we get?"
   - "What's the dress code?"
   - "Tell me about the probationary period"

### Verify Grounding
- Check that answers include policy numbers
- Verify citations match the source documents
- Confirm the bot says "I don't have information about that" for off-topic questions
- For Path 2: verify the Foundry agent tool is being invoked (check the activity trace in the Test pane)

## Troubleshooting

| Issue | Solution |
|---|---|
| No results returned | Verify AI Search index has documents (`/api/knowledge-base`) |
| Wrong policies cited | Check synonym maps and field mappings |
| Generic answers | Ensure generative answers system message enforces grounding |
| Connection failed | Verify AI Search endpoint and API key |
| Foundry agent not invoked | Verify the tool is added and instructions mention policy queries |
| Foundry agent timeout | Check Foundry project endpoint and managed identity RBAC |

## Limitations and Mitigations

These are the challenges addressed by the two-path approach:

| # | Limitation (Path 1 alone) | Mitigation |
|---|--------------------------|------------|
| 1 | **No vector/hybrid search (legacy index)** | Use integrated vectorization index (supports vector queries natively), or use Path 2 for agentic retrieval |
| 2 | **Instructions, not system messages** | Path 2 Foundry Agent has full custom retrieval + answer instructions in `search_config.json` |
| 3 | **No glossary expansion in instructions** | Synonym map handles this at the index level; Path 2 agent also applies Python-side expansion |
| 4 | **Knowledge source limits** (25 sources max) | Path 2 Knowledge Base aggregates multiple sources; the agent uses descriptions to filter |
| 5 | **Limited citation control** | Path 2 provides structured citations with policy numbers via agent instructions |
| 6 | **Semantic search quota** | `free` tier: 1,000 queries/month — upgrade for production |
| 7 | **No query planning** | Path 2 agentic retrieval performs LLM-driven subquery decomposition |

### Using Integrated Vectorization with Copilot Studio

Copilot Studio supports indexes built with [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization). When the index has an AzureOpenAI vectorizer configured, Copilot Studio can leverage the vector search capability automatically. This eliminates limitation #1 above.

To use integrated vectorization with Copilot Studio:

1. Deploy the integrated vectorization index using the `IntegratedVectorizationSearchService.create_index()` method or set up the indexer + skillset pipeline in the Azure portal
2. The index includes an `AzureOpenAIVectorizer` that handles query-time text-to-vector conversion
3. In Copilot Studio, add the index as an Azure AI Search knowledge source (same steps as the legacy index)
4. Copilot Studio will automatically use the vectorizer for hybrid (text + vector + semantic) search

See:
- [Azure AI Search integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Copilot Studio - Add Azure AI Search as a knowledge source](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)

For production, consider using both paths:
- **Path 1** for simple, fast Q&A with direct search
- **Path 2** for complex queries that need agentic retrieval, multi-source aggregation, and detailed citations

## Web Chat Embed Frontend

This project includes a dedicated React frontend that embeds the Copilot Studio agent using the Bot Framework Web Chat SDK.

### Running the Frontend

```bash
cd src/frontend-copilot-studio
npm install
npm run dev
# Available at http://localhost:5174
```

### Two Chat Modes

| Mode | Description |
|---|---|
| **Web Chat Embed** | Full Bot Framework Web Chat widget connected via Direct Line token. Supports rich cards, adaptive cards, and all Copilot Studio features. |
| **Backend Proxy** | Simple chat UI that routes messages through the FastAPI backend (`/api/copilot-studio/chat`). Useful for testing or when the Direct Line token endpoint isn't accessible. |

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `COPILOT_STUDIO_ENVIRONMENT_ID` | Power Platform environment ID (e.g. `<your-environment-id>`) | Yes |
| `COPILOT_STUDIO_AGENT_SCHEMA` | Agent schema name (e.g. `<your_agent_schema>`) | Yes |
| `COPILOT_STUDIO_REGION` | Region (default: `unitedstates`) | No |
| `COPILOT_STUDIO_TOKEN_ENDPOINT` | Full token endpoint URL (override) | No |

### References

- [Azure AI Search knowledge in Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)
- [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent)
- [Azure AI Search integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Foundry IQ Agents Lab](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.4-microsoft-foundry-agentic-retrieval/notebooks/foundry-IQ-agents.ipynb)
- [Advanced Querying with AI Search in Copilot Studio](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.1-ai-search-advanced/2.1-ai-search-advanced.md)
- [Azure-Samples/Copilot-Studio-with-Azure-AI-Search](https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search)
