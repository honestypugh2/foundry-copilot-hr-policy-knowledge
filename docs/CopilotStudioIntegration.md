# Copilot Studio Integration Guide

Use this document as the detailed Copilot Studio field reference. Choose one
pattern below and follow its short guide first. Each pattern can be built and
tested independently; do not combine routes until each one passes by itself.

## Choose one pattern

| Pattern | Choose it when | Copilot Studio connection | Build guide | Detailed reference |
| --- | --- | --- | --- | --- |
| **A — Direct index** | You want the simplest policy Q&A with native citations. | Azure AI Search knowledge source | [Build A](patterns/pattern-a-direct-index.md) | [A wiring](#pattern-a-wiring) |
| **A-SP — SharePoint** | Policies already live in SharePoint and per-user file access matters. | SharePoint knowledge source | [A-SP wiring](#pattern-a-sp-wiring) | [A-SP wiring](#pattern-a-sp-wiring) |
| **A2 — Direct Foundry IQ** | Retrieval needs query planning, but Copilot Studio should write the answer. | Foundry IQ knowledge-base tool | [Build A2](patterns/pattern-a2-foundry-iq.md) | [A2 wiring](#pattern-a2-wiring-github-copilot-harness--foundry-iq) |
| **B — Foundry agent** | Foundry must force retrieval and own answer synthesis. | External Microsoft Foundry agent | [Build B](patterns/pattern-b-foundry-agent.md) | [B wiring](#pattern-b-wiring) |
| **C — Document locator** | The user needs the exact authoritative filename and URL, not a summary. | REST API tool, `lookupHRPolicyDocument` | [Build C](patterns/pattern-c-document-locator.md) | [C wiring](#pattern-c-wiring) |
| **Hosted — Agent Framework** | You must own the runtime, middleware, authentication, or request loop. | External Foundry agent backed by your container | [Build Hosted](patterns/pattern-hosted-agent.md) | [Hosted wiring](#hosted-agent-wiring) |

**Stop after one pattern** if it meets the requirement. Use the
[hybrid guide](CopilotStudioHybridExample.md) only after the individual routes
pass in separate test agents. See [RetrievalPatterns.md](RetrievalPatterns.md)
for the full architecture comparison and the
[Copilot Studio Testing Guide](CopilotStudioTestingGuide.md) for validation.

Older material calls Pattern A "Path 1" and Pattern B "Path 2".

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

## Shared prerequisites

| Requirement                     | Details                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| Copilot Studio license          | Power Virtual Agents / Copilot Studio                                |
| Power Platform environment      | (your environment ID)                                                |
| Azure AI Search index           | `hr-policy-index` (deployed via this project)                        |
| Azure AI Search access (Entra ID) | Data connection with **Entra ID** auth; grant **Search Index Data Reader** to the Copilot Studio agent identity and the unique `HRPolicyAgent` identity for Pattern B |
| Microsoft Foundry project       | Required for **A2, B, and Hosted**                                   |
| RBAC: Search Index Data Reader  | Assigned to the unique `HRPolicyAgent` Entra identity (Pattern B only) |

---

<a id="pattern-a-wiring"></a>

## Pattern A wiring — Azure AI Search as Knowledge Source

> **Have your policies in SharePoint already?** Skip this section and
> use [Pattern A-SP](#pattern-a-sp-wiring) instead. It's the same
> wiring story — a Copilot Studio Knowledge Source attached to the
> agent — but you point at a SharePoint document library through CS's
> native connector and inherit deep-link citations + per-user
> permissions for free. No `hr-policy-index` ingestion required.

### A1: Create a Copilot in Copilot Studio

1. Navigate to [Copilot Studio](https://copilotstudio.microsoft.com).
2. Click **Create → New copilot**.
3. Name: `Ask HR Policy Agent`.
4. Description: `Answers employee questions using internal HR policy documents`.
5. Language: English.

### A2: Add Azure AI Search as a Knowledge Source

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

<a id="pattern-a2-wiring-github-copilot-harness--foundry-iq"></a>

## Pattern A2 wiring — GitHub Copilot harness to Foundry IQ

Steps 1–2 above wire **Pattern A** — the *classic search* path, connecting
Copilot Studio to an Azure AI Search **index**. The Copilot Studio **new agent
experience**, now documented as the **GitHub Copilot harness**, adds a second,
distinct front door: connect the agent **directly to a Foundry IQ knowledge
base** (`hr-knowledge-base`) as a **Foundry IQ tool**. This is **agentic
retrieval** — the knowledge base plans sub-queries, retrieves in parallel,
reranks, and returns merged results — and it needs **no Foundry prompt agent**
in the path.

> **Availability (verified August 6, 2026).** Microsoft Learn no longer labels
> the Copilot Studio GitHub Copilot harness or its Foundry IQ connection as
> preview. Foundry IQ has mixed availability: some agentic-retrieval features
> are GA through the `2026-04-01` REST API, while the Microsoft Foundry and
> Azure portal experiences continue to provide preview-only access to the full
> feature set. Review the API version and feature-specific status before using
> this path in production.

> **Prerequisite.** Provision the knowledge base first:
> `python -m src.agents.create_foundry_agent` (it creates the Knowledge Source
> and `hr-knowledge-base`; the PromptAgent it also creates is not required for
> Pattern A2). Copilot Studio and the Foundry project must share the same Entra
> tenant, and you must have access to the knowledge base in Microsoft Foundry.

1. Open your agent (new experience) and select the **Build** tab.
2. In the components panel, select **Tools** → **Foundry IQ**.
3. Select **Create new connection**, choose an authentication type
   (**Microsoft Entra ID Integrated** recommended; API key / client certificate /
   service principal also supported), enter the Foundry IQ Search Service
   endpoint, and select **Create**.
4. Complete the UI path shown in your environment:
    - **Knowledge-base picker:** select **Next**, choose
      **`hr-knowledge-base`**, select **Add to agent**, then **Save**.
      - **Tool input check:** open the connected tool's **Inputs** page. The
         native binding shows **Messages (`object[]`)** with **How is this filled?**
         set to **AI**. Leave that setting unchanged. **Knowledge Base Name** and
         **API Version** aren't invocation inputs in this surface; Copilot Studio
         stores them in the knowledge-base selection and connection binding.
         They are established when you select **Next**, choose
         **`hr-knowledge-base`** from the picker, and select **Add to agent**. They
         can't be corrected later from the **Messages** input page.
      - If the action exposes only **Knowledge Base Name** and **API Version** and
         has no **Messages** input, it can't build the retrieval request body and
         fails with HTTP 400: `A non-empty request body is required`. Remove that
         action and add Foundry IQ again through the knowledge-base picker. If the
         picker is absent, verify that the agent was created with the GitHub
         Copilot harness.
5. Select the connected Foundry IQ knowledge base and give it a **detailed
   description** — the description drives orchestration. Paste the following,
   then select **Save**:

   ```text
   Search the authoritative internal HR policy knowledge base for questions
   about hiring, leave, pay, dress code, career paths, IT policies, ethics, and
   operational matters. Use this tool for factual or comparative HR policy
   questions. Search by policy number, formal title, and common employee terms.
   Do not use this tool for general-knowledge questions. If evidence is absent,
   say that the HR policy documents do not contain the answer.
   ```
6. Test on the **Preview** tab and open the **activity trace**; confirm a
   **Foundry IQ retrieval** step appears.

> **Why the inputs differ.** The native Foundry IQ binding owns the selected
> `hr-knowledge-base` resource and compatible API version, while the AI-filled
> **Messages** input supplies the required retrieval body at invocation time.
> Do not replace **Messages** with a fixed value or try to add hidden resource
> inputs manually.
>
> In Preview, expand the tool call and inspect **Input**. A correct binding must
> not send sample defaults such as `knowledgeBaseName: hr-policy-docs` or
> `api-version: 2025-05-01-preview`. If those values appear, remove the tool and
> add it again from the dedicated **Foundry IQ** card, completing the
> knowledge-base picker. Do not choose the **Azure - Foundry IQ** connector and
> then add its retrieval action directly. If the dedicated flow never presents
> a picker and only **Azure - Foundry IQ -> Foundry IQ Knowledge Retrieval
> (API)** is available, the current environment's connector surface can't
> establish the native binding. Capture the trace and raise it with Microsoft
> support. Re-adding that action doesn't change its hidden defaults.

#### A2 fallback when the dedicated Foundry IQ picker is unavailable

The Search endpoint can only be entered through **Build -> Tools -> Foundry IQ
-> Create new connection**. The supported flow then displays **Next** and a
knowledge-base picker.

Do not substitute **Connector -> Azure - Foundry IQ -> Foundry IQ Knowledge
Retrieval (API)** or **Foundry IQ Knowledge Retrieval (MCP)**. Their action
Inputs pages don't expose the Search endpoint or establish the native
knowledge-base binding. Entering only **Knowledge Base Name** and **API Version**
doesn't identify the Search service.

If the **Foundry IQ** tool card or its connection form isn't available in the
current environment, Pattern A2 can't be configured there through the supported
Copilot Studio UI. Capture the missing card/action Inputs and environment ID,
then open a Microsoft support request for the rollout or tenant configuration.
Use Pattern A (Azure AI Search knowledge) or Pattern C (the repository lookup
connector) until the native Foundry IQ flow is available.

### First-test connection consent

The first Preview request can pause with **Connect to continue** and an
**Azure - Foundry IQ** consent card. This occurs before retrieval and does not
mean the knowledge base failed.

1. Select **Allow** on the consent card.
2. Wait for the connection to report ready.
3. Select **Retry**, or start a new test session and send the query again.
4. Open the activity trace and confirm a **Foundry IQ retrieval** step.

If the card still says **I couldn't connect** after consent, open the connection
manager, reconnect the **Azure - Foundry IQ** connection, and retry. If the
activity card shows only manual **Knowledge Base Name** and **API Version**
inputs and no **Messages** input, the action can't create a retrieval body.
Remove it and follow steps 1–4 above.

Before recreating the tool, verify the Azure-side resources independently:

```bash
uv run python -m src.agents.create_foundry_agent --verify-only
```

The expected result is an existing `hr-policy-index`,
`hr-knowledge-source`, and `hr-knowledge-base`. If the knowledge base does not
appear in Copilot Studio's picker even though verification succeeds, confirm
that Copilot Studio and the Search service use the same Entra tenant and that
the signed-in maker has access to the knowledge base.

> **One Foundry IQ connection per agent.** Tune retrieval (sources, instructions,
> ranking) in **Microsoft Foundry**, not Copilot Studio. Removing the connection
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
> `hr-knowledge-base` in Microsoft Foundry without changing the Copilot Studio
> wiring.
>
> **When to use A2 vs B.** A2 connects Copilot Studio straight to the KB
> (simplest agentic path, new experience). Pattern B wraps the same KB in a
> Foundry prompt agent with `tool_choice="required"` and connects Copilot Studio
> to the *agent* — use B when you need forced grounding / answer synthesis owned
> in Foundry, or when you're on the classic Copilot Studio experience.
>
> **Reference:** [Connect to Foundry IQ from an agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/foundry-iq-connect).

<a id="a2-prompt-contract"></a>

### A2 prompt contract and sample queries

A2 has two instruction layers:

1. **Copilot Studio answer instructions:** use the shared instruction block in
   [shared Copilot instructions](#shared-copilot-instructions). Copilot Studio
   owns the final answer.
2. **Foundry IQ retrieval instructions:** the repository provisions these from
   `foundry_agent.retrieval_instructions` in
   [`src/config/search_config.json`](../src/config/search_config.json). They
   require retrieval only from connected sources, policy-number/title matching,
   multi-policy decomposition, and a grounded refusal when evidence is absent.

Try these in the Copilot Studio **Preview** pane:

| Query | Expected behavior |
| --- | --- |
| `Compare the uniform and non-uniform dress code policies.` | Foundry IQ retrieval for Policies 60010 and 60020, followed by a cited Copilot Studio answer. |
| `How do the HR Generalist and Data Management career paths differ?` | Multi-policy retrieval for Policies 40010 and 40020. |
| `What will the weather be tomorrow?` | Grounded refusal with no invented policy citation. |

Open the activity trace for each query and confirm that a **Foundry IQ
retrieval** step occurred. If it did not, strengthen the Foundry IQ tool
description added in A2 step 5.

<a id="shared-copilot-instructions"></a>

## Shared Copilot Studio settings

Apply these settings to each isolated Copilot Studio test agent unless its
pattern guide says otherwise.

### S1: Add agent instructions

By default, new agents use **generative orchestration**, which
automatically searches all knowledge sources added on the Knowledge
page. You do **not** need to modify the **Conversational boosting**
system topic — it isn't used in generative orchestration mode.

#### Instructions field

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

### S2: Configure generative AI

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

### S3: Configure vernacular handling

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

### ASP1: Create the agent

Identical to [A1](#a1-create-a-copilot-in-copilot-studio) — same name,
description, and language.
If you already created an agent for Pattern A, reuse it; A-SP can
co-exist with A on the same agent (the planner will just have two
Knowledge Sources to choose from).

### ASP2: Add SharePoint as a Knowledge Source

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

### ASP3: Configure agent instructions and generative AI settings

Use the [shared Copilot Studio settings](#shared-copilot-studio-settings).
The instructions tell the planner how
to cite policy numbers and refuse off-topic questions; that logic is
independent of which Knowledge Source backs the answer.

> **No synonym map.** Pattern A-SP can’t use the `hr-glossary-synonyms`
> synonym map (it lives on `hr-policy-index`). If you need vernacular
> handling (“vacation” → “Paid Time Off”), either:
> 1. Wire **both** A and A-SP on the same agent so vernacular queries
>    can fall through the AI Search synonym map; or
> 2. Add a **Custom topic** with explicit trigger phrases for the
>    most-confused terms (see Pattern A Step 4.3).

### ASP4: Layering with other patterns

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

> **Shared setup.** Before adding the tool, complete
> [Shared Copilot Studio settings](#shared-copilot-studio-settings).
> Instructions tell the agent how to format responses and cite policy
> numbers; Generative AI settings enable orchestration and disable
> general knowledge. Pattern A Step 2 (Add Azure AI Search Knowledge
> Source) is **optional** for Pattern B — the Foundry agent runs its
> own retrieval pipeline.

### B1: Create the Foundry agent

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
| Search Index Data Reader        | User + `HRPolicyAgent` Entra identity          | Query indexes, access the knowledge base.        |
| Search Service Contributor      | Your user identity                             | Create knowledge bases and sources.              |

<a id="step-6-add-the-foundry-agent-to-copilot-studio"></a>

### B2: Add the Foundry agent to Copilot Studio

**Option A — Add the Foundry Agent directly:**

> **Standard harness required.** **Connect to an external agent** is a standard-
> harness feature. It doesn't appear in the GitHub Copilot-harness agent used
> for Pattern A2. Create a standard-harness Copilot Studio agent for Pattern B.
>
> **⚠️ New Foundry portal only.** Copilot Studio can only connect to Foundry
> agents created in the **new Foundry portal**; a previous-portal agent fails
> with `404 - Version not found`. This repo's `create_foundry_agent.py` uses the
> GA `azure-ai-projects` SDK (new Foundry), so `HRPolicyAgent` is compatible.

#### Enable the Activity protocol first

New Foundry agents expose the **Responses protocol** by default. Copilot
Studio's **Connect to an external agent** feature sends Activity protocol
messages, so a Responses-only endpoint fails with:

```text
Agent HRPolicyAgent endpoint does not support activity.
```

1. In the Microsoft Foundry portal, open `HRPolicyAgent`.
2. Select **Publish -> Teams and Microsoft 365 Copilot**.
3. Complete the metadata and publish options. For an isolated test, choose
   **Just you**.
4. Return to the agent details and confirm the endpoint shows **Activity
   protocol**.

The publish flow creates or configures Azure Bot Service and enables Activity
protocol with the matching channel authorization scheme. It requires
**Foundry User** on the project and **Azure Bot Service Contributor Role** (or
equivalent permissions) on the target resource group.

New-model Foundry agents can expose multiple protocols simultaneously. The
publish flow adds Activity and its Bot Service authorization scheme; Responses
may remain available for direct API clients.

This agent uses the new Foundry model, so publishing doesn't replace its unique
Entra identity. Confirm the `HRPolicyAgent` identity still has **Search Index
Data Reader** on the Search service before testing retrieval.

1. **Agents → Add an agent → Connect to an external agent → Microsoft Foundry (Preview)**.
2. Select an existing **connection**, or create one with your **Foundry project
   endpoint URL**, then select **Next**.
3. Complete **Connect Microsoft Foundry agent** with these values:

   | Field | Value |
   | --- | --- |
   | **Name** | `HRPolicyAgentB` |
   | **Description** | `Use this agent for every question about internal HR policies, including hiring, leave, pay, dress code, career paths, ethics, IT policies, and operational matters. It retrieves authoritative HR policy evidence, compares policies when needed, and returns policy-number and title citations. Do not use it for general-knowledge questions.` |
   | **Agent Id** | `HRPolicyAgent` |
   | **Connection** | The Microsoft Foundry connection created with `AZURE_AI_PROJECT_ENDPOINT` |

   **Name** is the local sub-agent label used by Copilot Studio. **Agent Id** is
   the stable Foundry agent identifier; it isn't the immutable agent-version
   number.
4. Under **Completion**, select **Write the response with generative
   AI** (lets Copilot Studio format the answer with citations).
5. Select **Add Agent**, then **Save**.

#### Get the Pattern B Agent ID

The provisioning command prints the created agent and version:

```bash
source .venv/bin/activate
python -m src.agents.create_foundry_agent
```

For this repository, `AGENT_NAME = "HRPolicyAgent"`, so the Copilot Studio
**Agent Id** is `HRPolicyAgent`. To verify an existing deployment without
creating a new version, run:

```bash
source .venv/bin/activate
python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env')

import os
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    credential=AzureCliCredential(process_timeout=30),
)
agent = client.agents.get(agent_name="HRPolicyAgent")
print(agent.id)
PY
```

Expected output:

```text
HRPolicyAgent
```

The signed-in identity needs permission to read agents in the Foundry project.
An HTTP 403 mentioning `agents/read` indicates missing Foundry project RBAC,
not an invalid Agent ID.

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

### B3: Wire the tool in Topics (optional)

If you prefer explicit routing instead of generative orchestration:

1. **Topics →** create or edit a topic.
2. **+ → Add a tool** → select the Foundry agent tool.
3. Map the user's message to the `query` input.
4. Under **Completion**, author a specific response template
   referencing output variables.

<a id="pattern-b-prompt-contract"></a>

### Pattern B prompt contract and sample queries

Pattern B also has two instruction layers, but Foundry owns the answer:

1. **Copilot Studio routing/formatting:** reuse the
   [shared Copilot instructions](#shared-copilot-instructions) so policy
   questions route to the external agent and general knowledge stays disabled.
2. **PromptAgent system instructions:**
   `_build_prompt_agent_definition()` in
   [`src/agents/create_foundry_agent.py`](../src/agents/create_foundry_agent.py)
   installs the prompt. It requires `knowledge_base_retrieve` first, prohibits
   general-knowledge answers, requires policy-number/title citations, provides
   grounded refusal behavior, and prohibits legal advice. It embeds the full
   retrieval and answer guidance from
   [`src/config/search_config.json`](../src/config/search_config.json), while
   `tool_choice="required"` enforces the MCP retrieval call.

Do **not** paste the PromptAgent system prompt into Copilot Studio. Change the
provisioned prompt or shared config and rerun
`python -m src.agents.create_foundry_agent`. The optional `/api/chat` route also
passes `AGENT_INSTRUCTIONS` from
[`src/agents/hr_policy_agent.py`](../src/agents/hr_policy_agent.py) for its
individual Responses API invocation; that overlay is not used when Copilot
Studio connects directly to the external PromptAgent.

Try these in Copilot Studio or the Foundry agent playground:

| Query | Expected behavior |
| --- | --- |
| `Explain the differences between full-time and part-time PTO and cite both policies.` | Required MCP retrieval and citations to Policies 50010 and 50020. |
| `Summarize the pre-employment medical examination and probationary-period requirements.` | Multi-policy synthesis from Policies 20010 and 20030. |
| `What will the weather be tomorrow?` | Grounded refusal after retrieval finds no policy evidence. |

---

<a id="pattern-c-wiring"></a>

## Pattern C wiring — Deterministic document locator

Pattern C is a separate locator route. It returns authoritative document
metadata from `POST /api/lookup`; it does not synthesize policy content.

1. Verify
   `https://ca-backend-zptc7utdm2gis.nicedune-3f634c43.eastus2.azurecontainerapps.io/api/health`.
2. Import [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json)
   through **Tools → Add a tool → New tool → REST API**.
3. For this public demo endpoint, select **None** for authentication. Use OAuth
   2.0 after enabling Container Apps Entra authentication.
4. Confirm the user's locator request maps to the required `query` input.
5. Add the
   [Pattern C router instructions](CopilotStudioLookupRouting.md#pattern-c-router-instructions).
6. Start a new test session and ask:
   `Give me the link to the part-time PTO policy.`
7. Pass when `lookupHRPolicyDocument` returns Policy 50020's exact filename and
   blob URL without replacing it with a summary.

Use the [Pattern C guide](patterns/pattern-c-document-locator.md) for the short
build path and [the routing reference](CopilotStudioLookupRouting.md) for all
fields, authentication options, and mixed content/location routing.

---

<a id="hosted-agent-wiring"></a>

## Hosted Agent wiring — Self-hosted container as a Tool

This path runs the same answer loop as Pattern B — `gpt-5-mini` synthesising
over an Azure AI Search retrieval tool — but inside your own container
([`src/hosted_agent/server.py`](../src/hosted_agent/server.py)). Use it
when you need custom auth, sidecar services, or full control of the
runtime. **Copilot Studio is still the front door**; only the agent's
request/response loop moves to your infrastructure.

> **Shared setup.** Complete
> [Shared Copilot Studio settings](#shared-copilot-studio-settings) before
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
protocol on `protocols/openai/responses` for direct tests. Before using
Copilot Studio's Foundry-agent connector, publish it to Teams and Microsoft
365 Copilot to enable Activity protocol; no REST API tool import is needed.

Verify deployment from the Foundry portal:

- Project → Agents tab → `hr-policy-agent` listed alongside `HRPolicyAgent`.
- Status: **Running**.
- Endpoint: `{project_endpoint}/agents/hr-policy-agent/endpoint/protocols/openai/responses`.

**RBAC requirements** — assign Search Index Data Reader to the hosted runtime
identity that reads `hr-policy-index` directly.

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

No additional Copilot Studio Instructions are required beyond the
[shared settings](#shared-copilot-studio-settings). If you also want Pattern C-style dual-tool
routing on top of the Hosted Agent, follow
[CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) verbatim
— the lookup tool is independent of which content agent you've wired.

<a id="hosted-prompt-contract"></a>

### Hosted prompt contract and sample queries

The server-side `HR_POLICY_SYSTEM_PROMPT` requires `search_hr_policies` before
every answer, prohibits general-knowledge answers, requires policy-number/title
citations, and asks a clarifying question for ambiguous requests. Copilot Studio
uses the [shared instructions](#shared-copilot-instructions) only for routing
and presentation; the container owns retrieval and synthesis.

Do **not** paste this server-side prompt into Copilot Studio. Edit
`HR_POLICY_SYSTEM_PROMPT` in
[`src/agents/hr_policy_agent_af.py`](../src/agents/hr_policy_agent_af.py), then
rebuild and redeploy the container for changes to take effect.

Try these in Copilot Studio or against the hosted Responses endpoint:

| Query | Expected behavior |
| --- | --- |
| `Compare Policies 50010 and 50020.` | A `search_hr_policies` tool call followed by a cited comparison. |
| `Which IT policies govern employee devices, acceptable use, and information security?` | Multi-policy retrieval for Policies 70070, 70010, and 70020. |
| `What will the weather be tomorrow?` | Tool call followed by the configured grounded-refusal response. |

---
## Publish and test

### Publish to Teams

1. **Channels → Microsoft Teams**.
2. Click **Turn on Teams**.
3. Configure:
   - Display name: `Ask HR`.
   - Description: `Ask questions about HR policies`.
4. Click **Publish**.
5. Share the bot link with employees.

### Validate the selected pattern

Use the corpus-grounded
[starter query catalog](CopilotStudioTestingGuide.md#starter-query-catalog) for
pattern-specific prompts and expected policy evidence. For a quick smoke test,
try these in the Copilot Studio **Test** pane:

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
| `Agent HRPolicyAgent endpoint does not support activity` | Publish `HRPolicyAgent` to **Teams and Microsoft 365 Copilot** in Foundry to enable Activity protocol, then retry with the same Agent Id. |
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
- [Microsoft Copilot Studio + Microsoft Foundry lab — 2.4](https://github.com/microsoft/Copilot-Studio-and-Azure)
- [Advanced Querying with AI Search in Copilot Studio](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.1-ai-search-advanced/2.1-ai-search-advanced.md)
- [Azure-Samples/Copilot-Studio-with-Azure-AI-Search](https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search)
- Reference repo: [honestypugh2/foundry-copilot-search-validate](https://github.com/honestypugh2/foundry-copilot-search-validate)
