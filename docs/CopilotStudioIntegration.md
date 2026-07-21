# Copilot Studio Integration Guide

This document describes how to connect **Copilot Studio** to the HR
Policy Knowledge Agent so employees can ask HR questions directly from
a Teams bot or web chat.

> **Just want to test the patterns end-to-end?** See the dedicated
> **[Copilot Studio Testing Guide](CopilotStudioTestingGuide.md)** — it
> consolidates the per-pattern wiring below into a single walkthrough
> with numbered test scenarios for the Test pane.

> **Pattern naming — quick map.** This guide is structured around the
> four patterns in [docs/RetrievalPatterns.md](RetrievalPatterns.md):
>
> | Pattern in this repo | Section in this doc                 | Older name (Rosetta stone) |
> | -------------------- | ----------------------------------- | -------------------------- |
> | **Pattern A** — Direct Knowledge Base (Azure AI Search) | [Pattern A wiring](#pattern-a-wiring) | "Path 1 — Knowledge Source" |
> | **Pattern A-SP** — SharePoint Knowledge Source (CS native connector) | [Pattern A-SP wiring](#pattern-a-sp-wiring) | (new) |
> | **Pattern B** — Foundry Agent Service + MCP | [Pattern B wiring](#pattern-b-wiring) | "Path 2 — Foundry Agent Action" |
> | **Pattern C** — Dual-Tool Routing           | [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) | (new) |
> | **Hosted Agent** — Self-hosted Agent Framework runtime | [Hosted Agent wiring](#hosted-agent-wiring) | (new) |
> | **Hybrid** — Pattern A + B + C combined     | [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md) | (new) |
>
> Older lab material and earlier versions of this doc used "Path 1 / Path 2".
> Those phrases now refer to Patterns A and B respectively.
>
> **Pattern B vs. Hosted Agent.** Both publish a Foundry-visible agent
> that Copilot Studio adds via the same **Tools → Azure AI Foundry
> agent** picker. The only difference is *where the agent's request
> loop runs* — Pattern B is Foundry-managed; Hosted Agent runs in your
> own container ([`src/hosted_agent/`](../src/hosted_agent/)). Copilot
> Studio's wiring steps are identical from Step 6 onward, so the
> Hosted Agent section below is intentionally short.

---

## Two Routing Levers

Copilot Studio gives you exactly two levers to control which retrieval
path runs for a given user question. Every section below ties back to
one or both of them.

- **Lever 1 — Agent instructions / Topic trigger phrases.** Copilot
  Studio's planner reads the agent's `Instructions` (and any Topic
  triggers) to decide *which tool to call*. Make instructions explicit
  about intent ("locate document" vs. "explain policy content").
- **Lever 2 — Tool / OpenAPI description.** When you import a REST
  API tool (e.g. [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json)),
  the planner picks the operation based on its `summary` and
  `description`. Keep them short, action-oriented, and disjoint from
  sibling tools.

A worked example combining both levers — `lookupHRPolicyDocument`
(Pattern C) and `askHRPolicy` (Pattern B) on top of a Pattern A
knowledge source — lives in
[CopilotStudioHybridExample.md](CopilotStudioHybridExample.md).

---

## Pattern Comparison

| Aspect                   | **Pattern A** — Direct Knowledge Base   | **Pattern B** — Foundry Agent Service + MCP |
| ------------------------ | -------------------------------------- | ----------------------------------------- |
| **How it works**         | Copilot Studio queries `hr-policy-index` directly via its native Azure AI Search connector. Hybrid (text + vector + semantic) search via integrated vectorization. Copilot Studio's built-in LLM synthesizes the answer. | Copilot Studio invokes a Foundry Agent via **Agents → Add an agent → Connect to an external agent → Microsoft Foundry (Preview)** (or a **REST API tool**). The agent uses agentic retrieval for AI-planned query routing, sub-query decomposition, and source attribution with custom retrieval + answer instructions. |
| **Search type**          | Text + vector + semantic ranker (single query) | Agentic retrieval (query planning + sub-queries + semantic ranking + answer synthesis) |
| **Answer synthesis**     | Copilot Studio built-in LLM            | Foundry Agent (`gpt-5-mini`) with custom instructions |
| **Custom instructions**  | Limited (Copilot Studio Instructions field) | Full retrieval + answer instructions in `search_config.json` |
| **Source attribution**   | URL-based citations (`metadata_storage_path`) | Rich per-fact citations with policy numbers via agent instructions |
| **Latency**              | ~1–2 s                                | ~10–14 s                                |
| **Setup complexity**     | Lowest — attach KB, write instructions | Higher — requires Foundry project + RBAC + `create_foundry_agent.py` |
| **Best for**             | Simple Q&A, fast responses, "start here" demo | Complex queries, multi-source aggregation, force-grounded synthesis |

---

## Prerequisites

| Requirement                     | Details                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| Copilot Studio license          | Power Virtual Agents / Copilot Studio                                |
| Power Platform environment      | (your environment ID)                                                |
| Azure AI Search index           | `hr-policy-index` (deployed via this project)                        |
| Azure AI Search access (Entra ID) | Data connection with **Entra ID** auth; grant **Search Index Data Reader** to the Copilot Studio agent identity (and the Foundry project managed identity for Pattern B) |
| Azure AI Foundry project        | Required for **Pattern B** only                                      |
| RBAC: Search Index Data Reader  | Assigned to the Foundry project managed identity (Pattern B only)    |

## Architecture

```
Employee (Teams / Web) ──► Copilot Studio Agent
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Pattern A             Pattern B
            Knowledge Source     Foundry Agent Tool
            (Azure AI Search)      │
                    │              ▼
                    │         Foundry Agent (gpt-5-mini)
                    │              │
                    │         MCP Tool: knowledge_base_retrieve
                    │              │
                    │         Knowledge Base
                    │              │
                    └──────┬───────┘
                           ▼
                      hr-policy-index
                           │
                           ▼
                  Grounded HR Policy Answer
```

---

<a id="pattern-a-wiring"></a>
## Pattern A wiring — Azure AI Search as Knowledge Source

> **Have your policies in SharePoint already?** Skip this section and
> use [Pattern A-SP](#pattern-a-sp-wiring) instead. It's the same
> wiring story — a Copilot Studio Knowledge Source attached to the
> agent — but you point at a SharePoint document library through CS's
> native connector and inherit deep-link citations + per-user
> permissions for free. No `hr-policy-index` ingestion required.

### Step 1: Create a Copilot in Copilot Studio

1. Navigate to [Copilot Studio](https://copilotstudio.microsoft.com).
2. Click **Create → New copilot**.
3. Name: `Ask HR Policy Agent`.
4. Description: `Answers employee questions using internal HR policy documents`.
5. Language: English.

### Step 2: Add Azure AI Search as a Knowledge Source

> **Use a formal data connection with Entra ID — not API keys.**
> Per current Microsoft guidance
> ([Add Azure AI Search as a knowledge source](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)),
> add Azure AI Search through **Data sources → Azure AI Search** with
> **Microsoft Entra ID authentication**. Don't manually configure an
> endpoint and Admin Key: broken key-based connections are managed at the
> *environment level* and can prevent the Azure AI Search dialog from
> loading for **all** agents, with no UI to delete the faulty connection.
> Key-based auth also spreads a long-lived admin secret into Power
> Platform (OWASP A07 — identification & authentication failures).

1. In the copilot editor, go to the **Knowledge** page (or click
   **Add knowledge** from the **Overview** page).
2. Click **Add knowledge → Featured → Azure AI Search**.
3. Click **Create new connection**.
4. Authentication: choose one of the Entra ID options (in order of
   preference):

   | Authentication type              | When to use                                                        |
   | -------------------------------- | ------------------------------------------------------------------ |
   | **Microsoft Entra ID Integrated** | Recommended — no secrets; the signed-in maker/agent identity is used. |
   | **Service principal (Entra ID app)** | Automated/unattended provisioning across environments.          |
   | **Client Certificate Auth**      | Certificate-based enterprise auth.                                  |

   Grant the agent (or service principal) the **Search Index Data Reader**
   role on the Azure AI Search service so it can query the index.
5. Connection details:

   | Field                          | Value                                                       |
   | ------------------------------ | ----------------------------------------------------------- |
   | Azure AI Search Endpoint URL   | `https://<your-search-service>.search.windows.net`          |

6. Click **Create** — a green check mark confirms the connection.
7. Click **Next**.
8. Index name: `hr-policy-index` (only one vector index can be added per
   connection).
9. Click **Add to agent**.
10. Wait for status **In progress → Ready**.

> **Recovering a broken connection.** If a faulty (typically key-based)
> Azure AI Search connection was created and the dialog now fails to load,
> reset the agent's external access or delete and recreate the agent, then
> re-add Azure AI Search using **Data sources → Azure AI Search** with
> **Entra ID authentication**.
>
> **Private networking.** Copilot Studio supports Azure AI Search indexes
> behind a **private endpoint / VNet**. Configure
> [Virtual Network support for Power Platform](https://learn.microsoft.com/en-us/power-platform/admin/vnet-support-setup-configure)
> and a
> [private endpoint for Azure AI Search](https://learn.microsoft.com/en-us/azure/search/service-create-private-endpoint)
> for enterprise isolation.

> **Semantic Ranker.** The index is provisioned with `semanticSearch:
> 'free'` and a semantic configuration named `hr-semantic-config`
> (title → `title`, content → `content`, keywords → `category`).
> Copilot Studio uses the semantic ranker automatically when the index
> has a semantic configuration.
>
> **Vector Search.** Both indexing options configure an
> `AzureOpenAIVectorizer` (`text-embedding-3-small`), so Copilot Studio
> performs **hybrid (text + vector + semantic)** search out of the box
> — no Foundry project required for Pattern A.

### Pattern A2 wiring (new experience → Microsoft IQ → Foundry IQ)

Steps 1–2 above wire **Pattern A** — the *classic search* path, connecting
Copilot Studio to an Azure AI Search **index**. The Copilot Studio **new agent
experience** (preview) adds a second, distinct front door: connect the agent
**directly to a Foundry IQ knowledge base** (`hr-knowledge-base`) via
**Microsoft IQ**. This is **agentic retrieval** — the knowledge base plans
sub-queries, retrieves in parallel, reranks, and returns merged results — and it
needs **no Foundry prompt agent** in the path.

> **Prerequisite.** Provision the knowledge base first:
> `python -m src.agents.create_foundry_agent` (it creates the Knowledge Source
> and `hr-knowledge-base`; the PromptAgent it also creates is not required for
> Pattern A2). Copilot Studio and the Foundry project must share the same Entra
> tenant, and you must have access to the knowledge base in Azure AI Foundry.

1. Open your agent (new experience) and select the **Build** tab.
2. In the components panel, select **Microsoft IQ** → **Foundry IQ**.
3. Select **Create new connection**, choose an authentication type
   (**Microsoft Entra ID Integrated** recommended; API key / client certificate /
   service principal also supported), enter the Foundry IQ Search Service
   endpoint, and select **Create**.
4. Select **Next**, choose **`hr-knowledge-base`** from the list, and select
   **Add to agent**, then **Save**.
5. Select the connected Foundry IQ knowledge base and give it a **detailed
   description** — the description drives orchestration. Select **Save**.
6. Test on the **Preview** tab and open the **activity trace**; confirm a
   **Foundry IQ retrieval** step appears.

> **One Foundry IQ connection per agent.** Tune retrieval (sources, instructions,
> ranking) in **Azure AI Foundry**, not Copilot Studio. Removing the connection
> in Copilot Studio doesn't delete the knowledge base in Foundry.
>
> **Why Microsoft Entra ID Integrated matters (security trimming).** With
> **Entra ID Integrated** auth, the signed-in user's identity flows through to
> the knowledge base, so results are **ACL-trimmed per user** — each user only
> sees content they're authorized to access, with no extra configuration in
> Copilot Studio. The other auth types (API key / client certificate / service
> principal) query under a single shared identity and do **not** honor
> per-user ACLs, so prefer Entra ID Integrated whenever the underlying sources
> carry document-level permissions. Foundry IQ knowledge bases also carry
> enterprise-readiness controls (customer-managed keys, network isolation,
> Microsoft Entra ID, FedRAMP/SOC2 compliance) inherited from Azure AI Search —
> see [Azure AI Search security overview](https://learn.microsoft.com/en-us/azure/search/search-security-overview).
>
> **Multi-source federation.** A knowledge base can bundle **multiple**
> knowledge sources; agentic retrieval plans sub-queries and federates across
> them in parallel, then reranks the merged results. This repo provisions a
> single source (`hr-knowledge-source`), but you can add more sources to
> `hr-knowledge-base` in Azure AI Foundry without changing the Copilot Studio
> wiring.
>
> **When to use A2 vs B.** A2 connects Copilot Studio straight to the KB
> (simplest agentic path, new experience). Pattern B wraps the same KB in a
> Foundry prompt agent with `tool_choice="required"` and connects Copilot Studio
> to the *agent* — use B when you need forced grounding / answer synthesis owned
> in Foundry, or when you're on the classic Copilot Studio experience.
>
> **Reference:** [Connect to Foundry IQ from an agent (preview)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/foundry-iq-connect).

### Step 3: Configure Lever 1 — Agent Instructions

By default, new agents use **generative orchestration**, which
automatically searches all knowledge sources added on the Knowledge
page. You do **not** need to modify the **Conversational boosting**
system topic — it isn't used in generative orchestration mode.

#### 3a. Add Instructions (Overview page)

1. Open your agent in Copilot Studio.
2. On the **Overview** page, find the **Instructions** text box.
3. Paste:

   ```
   You are an HR policy assistant. Answer questions ONLY using the provided HR
   policy documents.

   - Always cite the specific policy number (e.g., Policy 50010).
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

1. Go to **Settings → Generative AI**.
2. **Use generative AI orchestration** → **Yes** (default).
3. Optional but recommended: **Allow the AI to use its own general
   knowledge** → **Off**, so the agent only answers from
   `hr-policy-index`.
4. **Content moderation** → **High** (default).
5. Click **Save**.

> **Note — Classic orchestration.** If you need classic orchestration
> instead, go to **Topics → System → Conversational boosting** and
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
   - "PTO", "time off", "vacation" ↔ "Paid Time Off"
   - "sick leave", "sick time", "std" ↔ "Short-Term Disability"
   - "dress code", "what to wear", "uniforms" ↔ "Uniform Dress Code"
   - _(Full glossary: 30+ mappings in `HR_GLOSSARY` dict.)_
2. **Python-side glossary expansion.** The backend API also applies
   `expand_query_with_glossary()` before sending queries to AI Search,
   for direct API consumers that don't go through Copilot Studio.
3. **Custom topic for common terms.** Optionally create a topic for
   frequently misunderstood terms:
   - Trigger: `What does [term] mean?`
   - Action: query the glossary endpoint `/api/glossary`.

---

<a id="pattern-a-sp-wiring"></a>
## Pattern A-SP wiring — SharePoint as a Knowledge Source

Pattern A-SP is the **SharePoint variant of Pattern A**. The agent’s
routing and instructions are identical — the only thing that changes
is the underlying Knowledge Source connector. Use it when your HR
policy documents already live in a SharePoint Online document library
and you want Copilot Studio to handle indexing, citations, and access
control natively.

> **Pattern A vs. Pattern A-SP — quick decision.** Pick **A-SP** when
> the documents already live in SharePoint and you want deep-link
> citations + per-user permissions out-of-the-box. Pick **A** when you
> need control of the index schema (synonym map, semantic config,
> custom fields like `policy_number`/`category`/`blob_url`), or when
> the source is anything other than SharePoint (blob, file share,
> third-party DMS).

### Comparison

| Aspect                | **Pattern A** (Azure AI Search) | **Pattern A-SP** (SharePoint connector) |
| --------------------- | ------------------------------- | --------------------------------------- |
| Knowledge Source type | Azure AI Search index `hr-policy-index` | SharePoint document library (CS native connector) |
| Ingestion pipeline    | This repo — indexer scripts + optional Logic Apps ([SharePointLogicAppsArchitecture.md](SharePointLogicAppsArchitecture.md)) | None — Microsoft 365 search indexes the library automatically |
| Citation surface      | Citation card pointing at `metadata_storage_path` (blob URL) | Direct deep link to the SharePoint file (`https://<tenant>.sharepoint.com/.../file.docx`) — native CS card |
| Auth model            | API key / managed identity (agent-wide) | Per-user OAuth via the SharePoint connection — agent inherits each caller’s SharePoint permissions |
| Synonym map / semantic config | Yes — `hr-glossary-synonyms` + `hr-semantic-config` honoured | No — you’re bound to Microsoft 365 search ranking |
| Custom fields available to the agent | Yes — `policy_number`, `category`, `blob_url`, etc. | No — only the title/snippet/URL the SP connector returns |
| Best for              | Custom retrieval tuning, controlled vocabularies, when docs aren’t in SharePoint | Docs already in SharePoint, deep-link citations, ACL-aware answers |

### Prerequisites

| Requirement | Details |
| ----------- | ------- |
| SharePoint document library | The library that holds the HR policy `.docx` / `.pdf` files (e.g. `https://<tenant>.sharepoint.com/sites/HRPolicies/Shared Documents/Policies`). |
| Per-user SharePoint access | Each end user must be able to open the documents in SharePoint — the connector enforces SharePoint ACLs at query time. |
| Microsoft 365 search has indexed the library | New / freshly uploaded files take up to ~15 minutes to surface. Verify with the SharePoint search bar before wiring. |
| Same tenant as Copilot Studio | The connector is OAuth-based; cross-tenant SharePoint sources aren’t supported. |

### Step 1: Create the agent

Identical to **Pattern A Step 1** — same name, description, language.
If you already created an agent for Pattern A, reuse it; A-SP can
co-exist with A on the same agent (the planner will just have two
Knowledge Sources to choose from).

### Step 2: Add SharePoint as a Knowledge Source

1. In the agent editor go to **Knowledge** (or click **Add knowledge**
   from the **Overview** page).
2. Click **Add knowledge → Featured → SharePoint**.
3. Sign in to the connector with an account that can read the target
   library. Copilot Studio creates a per-user connection.
4. Paste the **document library URL** (or a folder URL within the
   library) when prompted. For example:

   ```text
   https://<tenant>.sharepoint.com/sites/HRPolicies/Shared Documents/Policies
   ```

5. Optionally add a friendly name and description (the description
   feeds the planner — keep it short and focused on “HR policy
   documents” so it routes the right intents here).
6. Click **Add to agent**. Wait for status **In progress → Ready**.

> **Tenant search index.** Copilot Studio queries Microsoft 365 search
> under the covers, so the documents must already be discoverable in
> the SharePoint search bar. If a freshly-uploaded file isn’t found,
> wait for the next M365 crawl (~15 min) and re-test.

### Step 3: Configure agent Instructions and Generative AI settings

Use the **same Step 3a Instructions and Step 3b Generative AI
settings** as Pattern A above. The instructions tell the planner how
to cite policy numbers and refuse off-topic questions; that logic is
independent of which Knowledge Source backs the answer.

> **No synonym map.** Pattern A-SP can’t use the `hr-glossary-synonyms`
> synonym map (it lives on `hr-policy-index`). If you need vernacular
> handling (“vacation” → “Paid Time Off”), either:
> 1. Wire **both** A and A-SP on the same agent so vernacular queries
>    can fall through the AI Search synonym map; or
> 2. Add a **Custom topic** with explicit trigger phrases for the
>    most-confused terms (see Pattern A Step 4.3).

### Step 4: Layering with other patterns

Pattern A-SP composes with Patterns B, C, and Hosted exactly like
Pattern A:

- **A-SP + B / Hosted** — add the Foundry agent tool from
  [Pattern B wiring](#pattern-b-wiring) or [Hosted Agent wiring](#hosted-agent-wiring).
  Force-grounded synthesis runs against `hr-policy-index` under the
  Foundry agent’s control while plain content questions can still hit
  the SharePoint Knowledge Source.
- **A-SP + C** — add the lookup tool from
  [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md). The
  lookup tool needs `hr-policy-index` to be populated even if A-SP is
  the only content source, because `lookupHRPolicyDocument` reads
  metadata from the index.
- **A-SP-only** — perfectly valid as a minimal config. You get
  click-through deep links to the SharePoint files for free, and skip
  the indexer pipeline entirely.

> **Pattern A-SP and the Q3 callout.** Pattern A-SP is the canonical
> answer to README’s Q3 (“Are your docs in a citation-friendly
> Knowledge Source?”). Citations are deep links to SharePoint, so for
> simple “where is X?” intents you may not need Pattern C at all.

### Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| Knowledge source stuck on **In progress** | OAuth consent not granted, or the signed-in user lacks read access | Re-sign-in with an account that can open the library; check **Manage connections → SharePoint** for a green “Connected” status |
| New file not returned in answers | Microsoft 365 search hasn’t crawled the file yet | Confirm the file appears in the SharePoint search bar; wait ~15 min after upload |
| Citation deep link 404s for some users | Per-user SharePoint ACL doesn’t grant access | Grant the user **Read** on the library or specific file in SharePoint |
| Vernacular (“vacation” → PTO) misses | No synonym map on the SP connector | Add Pattern A alongside, or add a Custom topic for frequent terms |

---

<a id="pattern-b-wiring"></a>
## Pattern B wiring — Foundry Agent as a Tool

This path gives Copilot Studio access to the Foundry Agent's agentic
retrieval pipeline — AI-planned query routing, sub-query
decomposition, semantic ranking, answer synthesis, and custom
retrieval/answer instructions — all against the same
`hr-policy-index`.

> **Prerequisites from Pattern A.** Before adding the tool, complete
> Pattern A Step 3 (Instructions + Generative AI settings).
> Instructions tell the agent how to format responses and cite policy
> numbers; Generative AI settings enable orchestration and disable
> general knowledge. Pattern A Step 2 (Add Azure AI Search Knowledge
> Source) is **optional** for Pattern B — the Foundry agent runs its
> own retrieval pipeline.

### Step 5: Create the Foundry Agent

Run the provisioning script:

```bash
python -m src.agents.create_foundry_agent
```

This creates:

1. **Knowledge Source** (`hr-knowledge-source`) → points to `hr-policy-index`.
2. **Knowledge Base** (`hr-knowledge-base`) → wraps knowledge source(s).
3. **MCP connection** in the Foundry project (managed identity).
4. **Foundry Agent** (`HRPolicyAgent`, `gpt-5-mini`) with the
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

**Option A — Add the Foundry Agent directly:**

> **⚠️ New Foundry portal only.** Copilot Studio can only connect to Foundry
> agents created in the **new Foundry portal**; a previous-portal agent fails
> with `404 - Version not found`. This repo's `create_foundry_agent.py` uses the
> GA `azure-ai-projects` SDK (new Foundry), so `HRPolicyAgent` is compatible.

1. **Agents → Add an agent → Connect to an external agent → Microsoft Foundry (Preview)**.
2. Select an existing **connection**, or create one with your **Foundry project
   endpoint URL**, then select **Next**.
3. Enter a **Name** and **Description**, then enter the **Agent Id**
   (`HRPolicyAgent`). The Foundry agent runs as a sub-agent for complex tasks
   with agentic retrieval; you can change the Agent Id later from its details
   page.
4. Under **Completion**, select **Write the response with generative
   AI** (lets Copilot Studio format the answer with citations).
5. Select **Add Agent**, then **Save**.

See: [Add a Foundry agent to Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent).

**Option B — Add as a REST API tool (if the agent is deployed behind
an HTTP endpoint):**

If your Foundry Agent is exposed via an HTTP endpoint — in this repo the backend
runs on **Azure Container Apps** (`/api/chat`) — import
[`copilot/openapi-v2.json`](../copilot/openapi-v2.json):

> **Authentication is not Functions-specific.** Copilot Studio's REST API tool
> supports **None**, **API key**, or **OAuth 2.0**. Any HTTPS host works — you
> do **not** need Azure Functions. Choose by how the endpoint is protected:
>
> | Backend host | Auth to select |
> | ------------ | -------------- |
> | **Container Apps — public ingress** (default here) | **None** (demo only) |
> | **Container Apps — Entra auth** (`backendAuthClientId` set) | **OAuth 2.0** (Microsoft Entra ID) |
> | **Azure Functions** | **API key** — `code` in **Query** (or `x-functions-key` in **Header**) |
>
> **Prefer OAuth 2.0 (Entra) beyond a quick demo.** Every other hop uses Entra
> ID / managed identity; a function key or public ingress is a shared-secret /
> unauthenticated shortcut. **Managed identity does not apply to this hop** —
> Copilot Studio is a SaaS caller with no MI for outbound calls, so the
> Entra-aligned option is OAuth 2.0. (MI is correctly used for Foundry → Azure
> AI Search.)

1. **Tools → Add a tool → New tool → REST API**.
2. Upload `copilot/openapi-v2.json`.
3. Set **Authentication** per the table above (**None** for the default
   Container Apps public ingress, **OAuth 2.0** once Entra auth is enabled, or
   **API key** with `code` in **Query** only if hosted on Azure Functions).
4. Map the user's message to the `message` input parameter.
5. Under **Details**, ensure **Allow agent to decide dynamically when
   to use the tool** is checked.
6. Under **Completion**, select **Write the response with generative
   AI**.

> **UI Note.** Copilot Studio renamed *Actions* to *Tools* (April
> 2025+). The steps above reflect the current UI.

### Step 7: Wire the tool in Topics (optional)

If you prefer explicit routing instead of generative orchestration:

1. **Topics →** create or edit a topic.
2. **+ → Add a tool** → select the Foundry agent tool.
3. Map the user's message to the `query` input.
4. Under **Completion**, author a specific response template
   referencing output variables.

---
<a id="hosted-agent-wiring"></a>
## Hosted Agent wiring — Self-hosted container as a Tool

This path runs the same answer loop as Pattern B — `gpt-5-mini` synthesising
over an Azure AI Search retrieval tool — but inside your own container
([`src/hosted_agent/server.py`](../src/hosted_agent/server.py)). Use it
when you need custom auth, sidecar services, or full control of the
runtime. **Copilot Studio is still the front door**; only the agent's
request/response loop moves to your infrastructure.

> **Prerequisites from Pattern A.** Same as Pattern B — complete
> Pattern A Step 3 (Instructions + Generative AI settings) before
> adding the tool. Pattern A's Knowledge Source connection is optional;
> the hosted agent runs its own retrieval against the same
> `hr-policy-index` via the `@tool search_hr_policies` function.

### Step H1: Deploy the Hosted Agent container

Build and push the image, then publish the `agent.yaml` manifest to
your Foundry project so the agent shows up in the portal alongside
Pattern B's `HRPolicyAgent`.

```bash
cd src/hosted_agent
docker build -t hr-policy-agent:latest .
# Tag + push to your ACR, then deploy via az foundry agent create.
# Full deployment steps: ../../README.md §8 “Run the Hosted Agent runtime”
```

The agent manifest is [`src/hosted_agent/agent.yaml`](../src/hosted_agent/agent.yaml).
It names the agent `hr-policy-agent` and exposes the OpenAI Responses
protocol on `protocols/openai/responses`, which is exactly what
Copilot Studio's Foundry-agent connector consumes — no REST API tool
import needed.

Verify deployment from the Foundry portal:

- Project → Agents tab → `hr-policy-agent` listed alongside `HRPolicyAgent`.
- Status: **Running**.
- Endpoint: `{project_endpoint}/agents/hr-policy-agent/endpoint/protocols/openai/responses`.

**RBAC requirements** — same as Pattern B (Search Index Data Reader
for the project managed identity is enough; the container reads from
`hr-policy-index` directly).

### Step H2: Add the Hosted Agent to Copilot Studio

Identical to Pattern B Step 6 Option A:

1. **Agents → Add an agent → Connect to an external agent → Microsoft Foundry (Preview)**.
2. Select your AI Foundry project and **`hr-policy-agent`** (not
   `HRPolicyAgent` — that's Pattern B). Both are valid; pick one.
3. Under **Completion**, select **Write the response with generative
   AI** (lets Copilot Studio format the answer with citations).
4. Click **Save**.

> **REST API alternative.** If you'd rather front the container with
> your own HTTP endpoint (Azure Function, App Service, AKS ingress),
> follow Pattern B Step 6 Option B and import
> [`copilot/openapi-v2.json`](../copilot/openapi-v2.json) pointing at
> the container's URL. The OpenAPI shape (`/api/chat` → `askHRPolicy`)
> is the same.

### Step H3: Re-use Pattern B's routing and tool-description prompts

The Hosted Agent's **server-side system prompt** lives in
[`src/agents/hr_policy_agent_af.py:HR_POLICY_SYSTEM_PROMPT`](../src/agents/hr_policy_agent_af.py)
— functionally equivalent to Pattern B's `AGENT_INSTRUCTIONS` plus an
explicit "You MUST call `search_hr_policies` first" rule (the Agent
Framework runtime can't enforce `tool_choice="required"` server-side
the way Foundry Agent Service does).

No additional Copilot Studio Instructions are required beyond what you
set in **Pattern A Step 3**. If you also want Pattern C-style dual-tool
routing on top of the Hosted Agent, follow
[CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) verbatim
— the lookup tool is independent of which content agent you've wired.

---
## Publish and test

### Step 8: Publish to Teams

1. **Channels → Microsoft Teams**.
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
| Generic answers                | Pattern A — confirm "Allow general knowledge" is **off**. Pattern B — confirm the Foundry agent's `tool_choice="required"`. |
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
Studio uses the vector search capability automatically — which
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

## Consuming the published agent

Copilot Studio agents are consumed through Copilot Studio's **own
channels** — no custom web app is required. After publishing the agent
(**Publish**, then **Channels**):

| Channel                   | Use it for                                                                   |
| ------------------------- | ---------------------------------------------------------------------------- |
| **Demo website**          | A ready-to-share test site Copilot Studio generates for you. Best for demos. |
| **Microsoft Teams**       | Employees ask HR questions directly in Teams chat.                           |
| **Microsoft 365 Copilot** | Surface the agent in the flow of work as an M365 Copilot agent.              |
| **Custom website**        | Paste the generated Web Chat snippet into any existing page.                 |

This is how Copilot Studio agents are normally consumed, so a
hand-rolled Direct Line web app isn't needed for demos or production.

### Optional: Direct Line helper endpoints

For custom or proxied integrations, the FastAPI backend still exposes
two Direct Line helpers implemented in
[`src/copilot_studio/service.py`](../src/copilot_studio/service.py):

- `GET /api/copilot-studio/token` issues a short-lived Direct Line
  token, used to bootstrap a custom Web Chat embed without exposing the
  long-lived secret to the browser.
- `POST /api/copilot-studio/chat` proxies a single message to the
  Copilot Studio bot through Direct Line and returns the structured
  response.

> **Use the proxy only when you need to route chat through the FastAPI
> backend (e.g. for auth, audit logging, or rate limiting).** For plain
> user chat, prefer a Copilot Studio channel above — the proxy adds
> latency and an extra failure point.

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
- [Microsoft Copilot Studio + Azure AI Foundry lab — 2.4](https://github.com/microsoft/Copilot-Studio-and-Azure)
- [Advanced Querying with AI Search in Copilot Studio](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.1-ai-search-advanced/2.1-ai-search-advanced.md)
- [Azure-Samples/Copilot-Studio-with-Azure-AI-Search](https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search)
- Reference repo: [honestypugh2/foundry-copilot-search-validate](https://github.com/honestypugh2/foundry-copilot-search-validate)
