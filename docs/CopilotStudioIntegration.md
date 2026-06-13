# Copilot Studio Integration Guide

This document describes how to connect **Copilot Studio** to the HR
Policy Knowledge Agent so employees can ask HR questions directly from
a Teams bot or web chat.

> **Pattern naming \u2014 quick map.** This guide is structured around the
> four patterns in [docs/RetrievalPatterns.md](RetrievalPatterns.md):
>
> | Pattern in this repo | Section in this doc                 | Older name (Rosetta stone) |
> | -------------------- | ----------------------------------- | -------------------------- |
> | **Pattern A** \u2014 Direct Knowledge Base       | [Pattern A wiring](#pattern-a-wiring) | "Path 1 \u2014 Knowledge Source" |
> | **Pattern B** \u2014 Foundry Agent Service + MCP | [Pattern B wiring](#pattern-b-wiring) | "Path 2 \u2014 Foundry Agent Action" |
> | **Pattern C** \u2014 Dual-Tool Routing           | [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) | (new) |
> | **Hybrid** \u2014 Pattern A + B + C combined     | [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md) | (new) |
>
> Older lab material and earlier versions of this doc used "Path 1 / Path 2".
> Those phrases now refer to Patterns A and B respectively.

---

## Two Routing Levers

Copilot Studio gives you exactly two levers to control which retrieval
path runs for a given user question. Every section below ties back to
one or both of them.

- **Lever 1 \u2014 Agent instructions / Topic trigger phrases.** Copilot
  Studio's planner reads the agent's `Instructions` (and any Topic
  triggers) to decide *which tool to call*. Make instructions explicit
  about intent ("locate document" vs. "explain policy content").
- **Lever 2 \u2014 Tool / OpenAPI description.** When you import a REST
  API tool (e.g. [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json)),
  the planner picks the operation based on its `summary` and
  `description`. Keep them short, action-oriented, and disjoint from
  sibling tools.

A worked example combining both levers \u2014 `lookupHRPolicyDocument`
(Pattern C) and `askHRPolicy` (Pattern B) on top of a Pattern A
knowledge source \u2014 lives in
[CopilotStudioHybridExample.md](CopilotStudioHybridExample.md).

---

## Pattern Comparison

| Aspect                   | **Pattern A** \u2014 Direct Knowledge Base   | **Pattern B** \u2014 Foundry Agent Service + MCP |
| ------------------------ | -------------------------------------- | ----------------------------------------- |
| **How it works**         | Copilot Studio queries `hr-policy-index` directly via its native Azure AI Search connector. Hybrid (text + vector + semantic) search via integrated vectorization. Copilot Studio's built-in LLM synthesizes the answer. | Copilot Studio invokes a Foundry Agent as a Tool (via **Tools \u2192 Azure AI Foundry agent** or a **REST API tool**). The agent uses agentic retrieval for AI-planned query routing, sub-query decomposition, and source attribution with custom retrieval + answer instructions. |
| **Search type**          | Text + vector + semantic ranker (single query) | Agentic retrieval (query planning + sub-queries + semantic ranking + answer synthesis) |
| **Answer synthesis**     | Copilot Studio built-in LLM            | Foundry Agent (`gpt-4o`) with custom instructions |
| **Custom instructions**  | Limited (Copilot Studio Instructions field) | Full retrieval + answer instructions in `search_config.json` |
| **Source attribution**   | URL-based citations (`metadata_storage_path`) | Rich per-fact citations with policy numbers via agent instructions |
| **Latency**              | ~1\u20132 s                                | ~10\u201314 s                                |
| **Setup complexity**     | Lowest \u2014 attach KB, write instructions | Higher \u2014 requires Foundry project + RBAC + `create_foundry_agent.py` |
| **Best for**             | Simple Q&A, fast responses, "start here" demo | Complex queries, multi-source aggregation, force-grounded synthesis |

---

## Prerequisites

| Requirement                     | Details                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| Copilot Studio license          | Power Virtual Agents / Copilot Studio                                |
| Power Platform environment      | (your environment ID)                                                |
| Azure AI Search index           | `hr-policy-index` (deployed via this project)                        |
| Azure AI Search query key       | Reader access (query key sufficient for both patterns)               |
| Azure AI Foundry project        | Required for **Pattern B** only                                      |
| RBAC: Search Index Data Reader  | Assigned to the Foundry project managed identity (Pattern B only)    |

## Architecture

```
Employee (Teams / Web) \u2500\u2500\u25ba Copilot Studio Agent
                              \u2502
                    \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
                    \u25bc                   \u25bc
              Pattern A             Pattern B
            Knowledge Source     Foundry Agent Tool
            (Azure AI Search)      \u2502
                    \u2502              \u25bc
                    \u2502         Foundry Agent (gpt-4o)
                    \u2502              \u2502
                    \u2502         MCP Tool: knowledge_base_retrieve
                    \u2502              \u2502
                    \u2502         Knowledge Base
                    \u2502              \u2502
                    \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
                           \u25bc
                      hr-policy-index
                           \u2502
                           \u25bc
                  Grounded HR Policy Answer
```

---

<a id="pattern-a-wiring"></a>
## Pattern A wiring \u2014 Azure AI Search as Knowledge Source

### Step 1: Create a Copilot in Copilot Studio

1. Navigate to [Copilot Studio](https://copilotstudio.microsoft.com).
2. Click **Create \u2192 New copilot**.
3. Name: `Ask HR Policy Agent`.
4. Description: `Answers employee questions using internal HR policy documents`.
5. Language: English.

### Step 2: Add Azure AI Search as a Knowledge Source

1. In the copilot editor, go to the **Knowledge** page (or click
   **Add knowledge** from the **Overview** page).
2. Click **Add knowledge \u2192 Featured \u2192 Azure AI Search**.
3. Click **Create new connection**.
4. Authentication: **Access Key**.
5. Connection details:

   | Field                          | Value                                                       |
   | ------------------------------ | ----------------------------------------------------------- |
   | Azure AI Search Endpoint URL   | `https://<your-search-service>.search.windows.net`          |
   | Azure AI Search Admin Key      | Your API key (a query key is sufficient for read-only).     |

6. Click **Create** \u2014 a green check mark confirms the connection.
7. Click **Next**.
8. Index name: `hr-policy-index`.
9. Click **Add to agent**.
10. Wait for status **In progress \u2192 Ready**.

> **Semantic Ranker.** The index is provisioned with `semanticSearch:
> 'free'` and a semantic configuration named `hr-semantic-config`
> (title \u2192 `title`, content \u2192 `content`, keywords \u2192 `category`).
> Copilot Studio uses the semantic ranker automatically when the index
> has a semantic configuration.
>
> **Vector Search.** Both indexing options configure an
> `AzureOpenAIVectorizer` (`text-embedding-3-small`), so Copilot Studio
> performs **hybrid (text + vector + semantic)** search out of the box
> \u2014 no Foundry project required for Pattern A.

### Step 3: Configure Lever 1 \u2014 Agent Instructions

By default, new agents use **generative orchestration**, which
automatically searches all knowledge sources added on the Knowledge
page. You do **not** need to modify the **Conversational boosting**
system topic \u2014 it isn't used in generative orchestration mode.

#### 3a. Add Instructions (Overview page)

1. Open your agent in Copilot Studio.
2. On the **Overview** page, find the **Instructions** text box.
3. Paste:

   ```
   You are an HR policy assistant. Answer questions ONLY using the provided HR
   policy documents.

   - Always cite the specific policy number (e.g., Policy 51350).
   - If a policy doesn't cover the question, say so clearly.
   - Never provide legal advice.
   - Use professional, clear language.
   - Reference the exact policy title and section when possible.
   - Use FAQ documents only if the question is not relevant to a specific HR
     policy.
   ```

These instructions guide the planner when it decides which knowledge
sources to search, how to fill tool inputs, and how to generate
responses.

#### 3b. Configure Generative AI settings

1. Go to **Settings \u2192 Generative AI**.
2. **Use generative AI orchestration** \u2192 **Yes** (default).
3. Optional but recommended: **Allow the AI to use its own general
   knowledge** \u2192 **Off**, so the agent only answers from
   `hr-policy-index`.
4. **Content moderation** \u2192 **High** (default).
5. Click **Save**.

> **Note \u2014 Classic orchestration.** If you need classic orchestration
> instead, go to **Topics \u2192 System \u2192 Conversational boosting** and
> configure the generative answers node with specific knowledge
> sources and a system message. Generative orchestration is recommended
> for new agents.

### Step 4: Configure vernacular handling

Copilot Studio has limited prompt customization, so vernacular is
handled in three layers:

1. **Index-level synonym map (`hr-glossary-synonyms`).** The
   `create_index()` method in `search_service.py` attaches an Azure AI
   Search synonym map to the `title`, `content`, and `category` fields.
   It expands informal terms **at query time**, so Copilot Studio
   benefits even though it bypasses the Python backend:
   - "PTO", "time off", "vacation" \u2194 "Paid Time Off"
   - "sick leave", "sick time", "std" \u2194 "Short-Term Disability"
   - "dress code", "what to wear", "uniforms" \u2194 "Uniform Dress Code"
   - _(Full glossary: 30+ mappings in `HR_GLOSSARY` dict.)_
2. **Python-side glossary expansion.** The backend API also applies
   `expand_query_with_glossary()` before sending queries to AI Search,
   for direct API consumers that don't go through Copilot Studio.
3. **Custom topic for common terms.** Optionally create a topic for
   frequently misunderstood terms:
   - Trigger: `What does [term] mean?`
   - Action: query the glossary endpoint `/api/glossary`.

---

<a id="pattern-b-wiring"></a>
## Pattern B wiring \u2014 Foundry Agent as a Tool

This path gives Copilot Studio access to the Foundry Agent's agentic
retrieval pipeline \u2014 AI-planned query routing, sub-query
decomposition, semantic ranking, answer synthesis, and custom
retrieval/answer instructions \u2014 all against the same
`hr-policy-index`.

> **Prerequisites from Pattern A.** Before adding the tool, complete
> Pattern A Step 3 (Instructions + Generative AI settings).
> Instructions tell the agent how to format responses and cite policy
> numbers; Generative AI settings enable orchestration and disable
> general knowledge. Pattern A Step 2 (Add Azure AI Search Knowledge
> Source) is **optional** for Pattern B \u2014 the Foundry agent runs its
> own retrieval pipeline.

### Step 5: Create the Foundry Agent

Run the provisioning script:

```bash
python -m src.agents.create_foundry_agent
```

This creates:

1. **Knowledge Source** (`hr-knowledge-source`) \u2192 points to `hr-policy-index`.
2. **Knowledge Base** (`hr-knowledge-base`) \u2192 wraps knowledge source(s).
3. **MCP connection** in the Foundry project (managed identity).
4. **Foundry Agent** (`HRPolicyAgent`, `gpt-4o`) with the
   `knowledge_base_retrieve` MCP tool and `tool_choice="required"`.

Verify all resources exist:

```bash
python -m src.agents.create_foundry_agent --verify-only
```

**RBAC requirements:**

| Role                            | Assigned to                                    | Purpose                                          |
| ------------------------------- | ---------------------------------------------- | ------------------------------------------------ |
| Search Index Data Contributor   | Your user identity                             | Create indexes, upload documents.                |
| Search Index Data Reader        | User + Project Managed Identity                | Query indexes, access the knowledge base.        |
| Search Service Contributor      | Your user identity                             | Create knowledge bases and sources.              |

### Step 6: Add the Foundry Agent to Copilot Studio

**Option A \u2014 Add the Foundry Agent directly:**

1. **Tools \u2192 Add a tool \u2192 New tool \u2192 Azure AI Foundry agent**.
2. Select your AI Foundry project and `HRPolicyAgent`.
3. The Foundry agent runs as a sub-agent for complex tasks with agentic
   retrieval.
4. Under **Completion**, select **Write the response with generative
   AI** (lets Copilot Studio format the answer with citations).
5. Click **Save**.

See: [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent).

**Option B \u2014 Add as a REST API tool (if the agent is deployed behind
an HTTP endpoint):**

If your Foundry Agent is exposed via an Azure Function or FastAPI
endpoint, import [`copilot/openapi-v2.json`](../copilot/openapi-v2.json):

1. **Tools \u2192 Add a tool \u2192 New tool \u2192 REST API**.
2. Upload `copilot/openapi-v2.json`.
3. Authentication: API key \u2014 **Parameter name** `code`,
   **Location** `Query` (not `Header` \u2014 Azure Functions function keys
   return 401 against `Header`). Value: `az functionapp keys list -g <rg> -n <func> --query "functionKeys.default" -o tsv`.
4. Map the user's message to the `message` input parameter.
5. Under **Details**, ensure **Allow agent to decide dynamically when
   to use the tool** is checked.
6. Under **Completion**, select **Write the response with generative
   AI**.

> **UI Note.** Copilot Studio renamed *Actions* to *Tools* (April
> 2025+). The steps above reflect the current UI.

### Step 7: Wire the tool in Topics (optional)

If you prefer explicit routing instead of generative orchestration:

1. **Topics \u2192** create or edit a topic.
2. **+ \u2192 Add a tool** \u2192 select the Foundry agent tool.
3. Map the user's message to the `query` input.
4. Under **Completion**, author a specific response template
   referencing output variables.

---

## Publish and test

### Step 8: Publish to Teams

1. **Channels \u2192 Microsoft Teams**.
2. Click **Turn on Teams**.
3. Configure:
   - Display name: `Ask HR`.
   - Description: `Ask questions about HR policies`.
4. Click **Publish**.
5. Share the bot link with employees.

### Step 9: Testing

In the Copilot Studio **Test** pane, try:

- "What is the PTO policy?"
- "How many holidays do we get?"
- "What's the dress code?"
- "Tell me about the probationary period."

**Verify grounding:**

- Answers include policy numbers.
- Citations match the source documents.
- The bot says "I don't have information about that" for off-topic
  questions.
- For Pattern B: verify the Foundry agent tool is being invoked
  (activity trace in the Test pane).

---

## Troubleshooting

| Issue                          | Resolution                                                                        |
| ------------------------------ | --------------------------------------------------------------------------------- |
| No results returned            | Verify AI Search index has documents (`/api/knowledge-base`).                     |
| Wrong policies cited           | Check synonym maps and field mappings.                                            |
| Generic answers                | Pattern A \u2014 confirm "Allow general knowledge" is **off**. Pattern B \u2014 confirm the Foundry agent's `tool_choice="required"`. |
| Connection failed              | Verify AI Search endpoint and API key.                                            |
| Foundry agent not invoked      | Verify the tool is added and instructions mention policy queries.                 |
| Foundry agent timeout          | Check Foundry project endpoint and managed identity RBAC.                         |
| `askHRPolicy` returns 401      | Tool auth is `Header` instead of `Query`; switch to `Query` with parameter `code`.|

---

## Pattern A limitations and Pattern B mitigations

The challenges that motivate the two-pattern approach (and Pattern C
on top of either):

| # | Limitation (Pattern A alone)                | Mitigation                                                                                          |
| - | ------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1 | No vector / hybrid search on legacy indexes | Use the integrated-vectorization index (vector queries native), or use Pattern B for agentic retrieval. |
| 2 | Instructions, not full system messages      | Pattern B has full retrieval + answer instructions in `search_config.json`.                         |
| 3 | No glossary expansion in Copilot instructions | Synonym map handles this at the index level; Pattern B also applies Python-side expansion.          |
| 4 | Knowledge-source limit (25 sources max)     | Pattern B Knowledge Base aggregates multiple sources; the agent uses descriptions to filter.        |
| 5 | Limited citation control                    | Pattern B emits structured citations with policy numbers via agent instructions.                    |
| 6 | Semantic-search quota (`free` = 1k/month)   | Upgrade tier for production.                                                                         |
| 7 | No query planning                           | Pattern B agentic retrieval performs LLM-driven sub-query decomposition.                            |

### Using integrated vectorization with Pattern A

Copilot Studio supports indexes built with [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization).
When the index has an `AzureOpenAIVectorizer` configured, Copilot
Studio uses the vector search capability automatically \u2014 which
eliminates limitation #1.

To enable:

1. Deploy the integrated-vectorization index via
   `IntegratedVectorizationSearchService.create_index()` or set up the
   indexer + skillset pipeline in the Azure portal.
2. The index includes an `AzureOpenAIVectorizer` that handles
   query-time text-to-vector conversion.
3. In Copilot Studio, add the index as a knowledge source (same steps
   as Pattern A Step 2).
4. Copilot Studio will automatically use the vectorizer for hybrid
   (text + vector + semantic) search.

For production, consider running both patterns:

- **Pattern A** for simple, fast Q&A with direct search.
- **Pattern B** for complex queries that need agentic retrieval,
  multi-source aggregation, and detailed citations.
- **Pattern C** ([CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md))
  layered on top of either, for fast deterministic
  document-locator questions.

---

## Web Chat embed frontend

This project includes a dedicated React frontend
([`src/frontend-copilot-studio/`](../src/frontend-copilot-studio/))
that embeds the Copilot Studio agent using the Bot Framework Web Chat
SDK.

### Running the frontend

```bash
cd src/frontend-copilot-studio
npm install
npm run dev
# http://localhost:5174
```

### Two chat modes

| Mode             | Description                                                                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Web Chat embed** | Full Bot Framework Web Chat widget connected via Direct Line token. Supports rich cards, adaptive cards, and all Copilot Studio features. |
| **Backend proxy**  | Simple chat UI that routes messages through the FastAPI backend (`/api/copilot-studio/chat`). See *Direct Line proxy* below.              |

### Direct Line proxy (`/api/copilot-studio/token` + `/api/copilot-studio/chat`)

The FastAPI backend exposes two helper endpoints implemented in
[`src/copilot_studio/service.py`](../src/copilot_studio/service.py):

- `GET /api/copilot-studio/token` issues a short-lived Direct Line
  token, used to bootstrap the Web Chat embed without exposing the
  long-lived secret to the browser.
- `POST /api/copilot-studio/chat` proxies a single message to the
  Copilot Studio bot through Direct Line and returns the structured
  response.

> **Use the proxy when you want to route chat through the FastAPI
> backend (e.g. for auth, audit logging, or rate limiting). Otherwise
> embed Web Chat directly using the Direct Line token endpoint** \u2014
> the proxy adds latency and an extra failure point that aren't useful
> for plain user chat.

### Environment variables

| Variable                              | Description                                                  | Required |
| ------------------------------------- | ------------------------------------------------------------ | -------- |
| `COPILOT_STUDIO_ENVIRONMENT_ID`       | Power Platform environment ID.                               | Yes      |
| `COPILOT_STUDIO_AGENT_SCHEMA`         | Agent schema name (e.g. `<your_agent_schema>`).              | Yes      |
| `COPILOT_STUDIO_REGION`               | Region (default: `unitedstates`).                            | No       |
| `COPILOT_STUDIO_TOKEN_ENDPOINT`       | Full token endpoint URL (override).                          | No       |

---

## References

- [Azure AI Search knowledge in Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)
- [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent)
- [Azure AI Search integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Microsoft Copilot Studio + Azure AI Foundry lab \u2014 2.4](https://github.com/microsoft/Copilot-Studio-and-Azure)
- [Advanced Querying with AI Search in Copilot Studio](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.1-ai-search-advanced/2.1-ai-search-advanced.md)
- [Azure-Samples/Copilot-Studio-with-Azure-AI-Search](https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search)
- Reference repo: [honestypugh2/foundry-copilot-search-validate](https://github.com/honestypugh2/foundry-copilot-search-validate)
