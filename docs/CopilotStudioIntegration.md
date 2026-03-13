# Copilot Studio Integration Guide

This document describes how to connect **Copilot Studio** to the HR Policy Knowledge Agent's Azure AI Search index so employees can ask HR questions directly from a Teams bot or web chat.

## Prerequisites

| Requirement | Details |
|---|---|
| Copilot Studio license | Power Virtual Agents / Copilot Studio |
| Power Platform environment | `` |
| Azure AI Search index | `hr-policy-index` (deployed via this project) |
| Azure AI Search API key | Reader access (query key) |

## Architecture

```
Employee (Teams / Web) ──► Copilot Studio Bot
                              │
                              ▼
                          Knowledge Source
                          (Azure AI Search)
                              │
                              ▼
                         hr-policy-index
                              │
                              ▼
                     Grounded HR Policy Answer
```

## Step 1: Create a Copilot in Copilot Studio

1. Navigate to [Copilot Studio](https://copilotstudio.preview.microsoft.com/environments/9cb938ce-b109-e86f-99ee-7bad48b89f09/home)
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
> **Vector Search Limitation**: Copilot Studio's native Azure AI Search connector uses **text search + semantic ranker** only. It does **not** generate embeddings or execute vector queries. The `content_vector` field and hybrid (text + vector) search are only used when querying through the backend API (`/api/search` or the Agent Framework). This means Copilot Studio still gets high-quality results via BM25 + semantic reranking, but full hybrid search requires the backend.

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

## Step 5: Publish to Teams

1. Go to **Channels** → **Microsoft Teams**
2. Click **Turn on Teams**
3. Configure:
   - Display name: `Ask HR`
   - Description: `Ask questions about HR policies`
4. Click **Publish**
5. Share the bot link with employees

## Step 6: Testing

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

## Troubleshooting

| Issue | Solution |
|---|---|
| No results returned | Verify AI Search index has documents (`/api/knowledge-base`) |
| Wrong policies cited | Check synonym maps and field mappings |
| Generic answers | Ensure generative answers system message enforces grounding |
| Connection failed | Verify AI Search endpoint and API key |

## Limitations in Copilot Studio

These are the challenges that motivated building the full Agent Framework solution alongside Copilot Studio:

1. **No vector/hybrid search**: Copilot Studio queries AI Search with text + semantic ranker only; the backend API adds vector similarity via `content_vector` embeddings for higher recall. Copilot Studio does support [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization) indexes where the same embedding model is used for both indexing and querying.
2. **Instructions, not system messages**: In generative orchestration, agent behavior is guided by the **Instructions** field on the Overview page. These instructions influence tool/knowledge selection and response generation, but cannot modify search retrieval logic or override system-level behaviors.
3. **No glossary expansion in instructions**: Copilot Studio doesn't natively expand vernacular at the prompt level; the synonym map handles this at the index level, and the backend API adds Python-side expansion
4. **Knowledge source limits**: With generative orchestration, the agent searches up to 25 knowledge sources (file uploads don't count toward this limit). The agent uses descriptions to filter which sources to search.
5. **Limited citation control**: The backend provides structured citations with policy numbers. In Copilot Studio, citations require a URL field in the index (e.g., `metadata_storage_path`).
6. **Semantic search quota**: The `free` tier allows 1,000 semantic queries/month — sufficient for demos but requires upgrading for production
7. **Conversational boosting not used in generative mode**: With generative orchestration enabled (default), the Conversational boosting system topic is **not** used for knowledge searches. Customizations to that topic only apply in classic orchestration mode.

For production, consider using both:
- **Copilot Studio** for the Teams/web chat interface
- **Backend API** for complex queries that need the full orchestration pipeline

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
| `COPILOT_STUDIO_ENVIRONMENT_ID` | Power Platform environment ID | Yes |
| `COPILOT_STUDIO_AGENT_SCHEMA` | Agent schema name (e.g., `cr4ba_askHrPolicyAgent`) | Yes |
| `COPILOT_STUDIO_REGION` | Region (default: `unitedstates`) | No |
| `COPILOT_STUDIO_TOKEN_ENDPOINT` | Full token endpoint URL (override) | No |

### Azure AI Foundry Agent Integration

Copilot Studio can delegate to an Azure AI Foundry agent for advanced multi-step reasoning:

1. In Copilot Studio, go to **Actions** → **Add an action** → **Azure AI Foundry agent**
2. Select your AI Foundry project and the HR Policy Agent
3. The Foundry agent runs as a sub-agent for complex tasks

See: [Add a Foundry agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent)

### References

- [Azure AI Search knowledge in Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)
- [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent)
- [Azure-Samples/Copilot-Studio-with-Azure-AI-Search](https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search)
