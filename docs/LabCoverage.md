# Lab Coverage — Azure/Copilot-Studio-and-Azure

This repo implements (and extends, with the HR-policy use case) the
patterns established by the official Microsoft reference repo
[Azure/Copilot-Studio-and-Azure](https://github.com/Azure/Copilot-Studio-and-Azure).
This page is the cross-walk: each lab → our pattern(s) → what we add on top.

> **TL;DR.** All four labs are covered by Patterns A, B, and C in
> [RetrievalPatterns.md](RetrievalPatterns.md), with one deliberate
> deviation (Lab 2.3 — we use a Logic Apps + Document Intelligence
> pipeline instead of the SharePoint indexer for the reasons listed
> below) and one extension (Pattern C — sub-second deterministic
> document locator on top of Lab 2.4's Connected Agents pattern).

---

## Lab 1.4 — Use Azure AI Search in Copilot Studio

[Lab 1.4](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/1.4-ai-search/1.4-ai-search.md)
covers the basic flow: Storage Account → blob → Azure AI Search index
→ Copilot Studio **Knowledge → Add knowledge → Azure AI Search**.

| Lab 1.4 step                                          | This repo                                                                                  |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Storage account + blob container + upload PDF          | [`scripts/upload_to_blob.py`](../scripts/upload_to_blob.py), `data/knowledge_base/`        |
| Azure OpenAI embedding model deployed                  | `AZURE_OPENAI_DEPLOYMENT_NAME` + embeddings deployment from `infra/bicep/`                 |
| Azure AI Search resource + RAG-style index             | [`infra/bicep/`](../infra/) provisions `hr-policy-index` with vector + semantic config     |
| Vectorize data (integrated vectorization wizard)       | [`scripts/index_knowledge_base_integrated_vectorization.py`](../scripts/) — same outcome, scripted |
| Copilot Studio **Knowledge → Azure AI Search**         | **Pattern A** — see [CopilotStudioIntegration.md § Pattern A wiring](CopilotStudioIntegration.md#pattern-a-wiring) |
| Managed-identity appendix (`Storage Blob Data Reader`, `Cognitive Services OpenAI Contributor`) | Same RBAC model wired in `infra/bicep/main.bicep` |

**Where we extend:** the lab uses one PDF; our index has 14 HR policy
documents with policy-number / category / FAQ metadata, plus a
synonym map (`hr-glossary-synonyms`) for HR vernacular ("PTO" ↔ "Paid
Time Off") that operates at query time inside Copilot Studio. See
[CopilotStudioIntegration.md § Step 4: Vernacular handling](CopilotStudioIntegration.md).

---

## Lab 2.1 — Advanced AI Search querying (3 connection options)

[Lab 2.1](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.1-ai-search-advanced/2.1-ai-search-advanced.md)
shows three ways to wire AI Search into Copilot Studio plus advanced
index design (chunking, vectorization, semantic ranker, hybrid query
shape).

| Lab 2.1 element                                            | This repo                                                                                          |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Option 1** — AI Search as Knowledge Source               | **Pattern A** — [CopilotStudioIntegration.md § Pattern A wiring](CopilotStudioIntegration.md#pattern-a-wiring) |
| **Option 2** — Custom HTTP / Power Automate flow           | Functionally covered by **Pattern C** — we expose the search via a FastAPI endpoint (`POST /api/lookup`) instead of a Logic-Apps-style flow. Same shape: agent calls a custom HTTP action, parses JSON, generative-AI completion. See [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md). |
| **Option 3** — Custom Connector (Swagger / OpenAPI)        | **Pattern C** — [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json) is exactly a Swagger-defined REST tool imported into Copilot Studio. |
| Index design: chunking, embedding skill, semantic config, vector profile, HNSW, scoring | [`infra/bicep/main.bicep`](../infra/bicep/main.bicep), [`src/indexing/`](../src/indexing/), [DataPipelineAndTesting.md](DataPipelineAndTesting.md) — uses HNSW + scalar quantization (int8 with rescoring) for memory efficiency. |
| Hybrid + semantic + vector queries from Search explorer    | [`src/search/integrated_vectorization_search.py`](../src/search/) executes the same hybrid+semantic shape from Python; `tests/test_search.py` regression-guards it. |

**Where we extend:** Pattern C upgrades Option 3 from a *generic*
custom connector into a **deterministic locator tool** — the
`lookupHRPolicyDocument` operation returns `blob_url` /
`metadata_storage_path` verbatim with no LLM in the path
(~1–2 s vs ~10–14 s). The tool description mirrors the canonical
`file_metadata_lookup` definition from
[honestypugh2/foundry-copilot-search-validate](https://github.com/honestypugh2/foundry-copilot-search-validate/blob/main/src/agents/orchestrator_pattern_b.py)
so the same wording drives both Foundry-side and Copilot-Studio-side
routing.

---

## Lab 2.3 — SharePoint Indexer

[Lab 2.3](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.3-ai-search-sharepoint-indexer/2.3-ai-search-sharepoint-indexer.md)
uses the AI Search **SharePoint Online indexer** (preview) to pull
documents from a SharePoint document library directly into an index,
then attaches that index to Copilot Studio via Pattern A.

| Lab 2.3 element                                                          | This repo                                                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Microsoft Entra app registration with `Files.Read.All` + `Sites.Read.All` | Equivalent SharePoint connector auth in [SharePointLogicAppsArchitecture.md § Step 1](SharePointLogicAppsArchitecture.md) |
| Index optimised for SharePoint metadata (`metadata_spo_item_name`, etc.)  | Our `hr-policy-index` carries `source_library`, `sharepoint_site`, `file_name`, `last_modified`, `acl_hints` — same intent  |
| Skillset: `SplitSkill` + `AzureOpenAIEmbeddingSkill` + `indexProjections` | **Same skillset shape** in `infra/bicep/main.bicep` skillset definition + Logic App pipeline           |
| Indexer with hourly schedule (`PT1H`)                                     | Logic App SharePoint trigger fires per file event (more responsive than polling)                       |
| Connect index to Copilot Studio as Knowledge Source                       | **Pattern A** (identical wiring once the index is populated)                                            |

**Deliberate deviation — why we use Logic Apps + Document Intelligence
instead of the SharePoint indexer:**

| Need                                                              | SharePoint indexer (Lab 2.3) | Our Logic Apps pipeline |
| ----------------------------------------------------------------- | ---------------------------- | ----------------------- |
| Preview status                                                     | ⚠️ Preview                    | ✅ GA components         |
| Custom column extraction (policy_number, category from filename)  | ⚠️ `additionalColumns` only   | ✅ Logic App expressions can derive any field |
| Document Intelligence preprocessing (OCR, layout, tables)         | ❌ Not in pipeline             | ✅ DocIntel runs before chunking |
| Per-file event response (vs hourly poll)                          | ❌ Hourly minimum               | ✅ Trigger on create/modify |
| Private endpoints                                                  | ❌ Not supported                | ✅ Standard Logic App tier |

For HR-policy documents that need DocIntel preprocessing and
field-derivation logic, Logic Apps is the GA-supported path. For a
plain SharePoint library where the indexer's defaults are enough,
the Lab 2.3 path is simpler and is fully compatible with this repo's
Pattern A wiring — point a SharePoint indexer at the same
`hr-policy-index` schema and Copilot Studio doesn't know the
difference. See [SharePointLogicAppsArchitecture.md § Comparison](SharePointLogicAppsArchitecture.md#comparison-with-the-agent-framework-architecture).

---

## Lab 2.4 — Microsoft Foundry Agentic Retrieval (Foundry IQ + Connected Agents)

[Lab 2.4](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.4-microsoft-foundry-agentic-retrieval/README.md)
builds the Connected Agents pattern: a Foundry Agent does deep
multi-source agentic retrieval through Foundry IQ (Knowledge Base +
Knowledge Sources + MCP tool), and Copilot Studio orchestrates between
"quick lookups" (uploaded knowledge file) and "deep questions" (Foundry
agent call).

| Lab 2.4 element                                                                | This repo                                                                                          |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Foundry IQ Knowledge Source over an Azure AI Search index                       | `KnowledgeSource` provisioned by [`src/agents/create_foundry_agent.py`](../src/agents/create_foundry_agent.py) |
| Foundry IQ Knowledge Base aggregating sources                                   | Same — `KnowledgeBase` created by `create_foundry_agent.py`                                         |
| Fraud Analyst Agent with MCP tool calling the KB                                | **Pattern B** — `HRPolicyAgent` PromptAgentDefinition + MCPTool (`tool_choice="required"`)         |
| `gpt-4o` chat model + `text-embedding-3-large` embedding model                  | Modernized model surface — `AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini` (GPT-4o retired) + `text-embedding-3-small` embedding deployment from `infra`   |
| Required RBAC: `Search Index Data Reader` + `Search Service Contributor`        | Wired in `infra/bicep/main.bicep` for the project managed identity                                  |
| Copilot Studio orchestrator routes "quick lookup" vs "deep question"             | **Pattern C** — `copilot/openapi-lookup-v2.json` for fast deterministic lookup + Pattern A or B for content. See [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md). |
| **Hybrid scenarios** (combine quick refs + deep analysis in one answer)         | [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md) — same Connected Agents shape       |
| Educational-use disclaimer / same-tenant requirement                             | Same constraints apply — Foundry project + Copilot Studio must share the Entra tenant               |

**Where we extend:**

1. **Pattern C is sharper than the lab's "uploaded knowledge" lookup.**
   Lab 2.4 implements quick lookups via a static markdown file uploaded
   to Copilot Studio (`quick_reference_guide.md`). We back our quick
   path with a live `POST /api/lookup` against the same AI Search index
   the deep agent uses, so the locator answer is always in sync with
   the knowledge base — no second source of truth to maintain.
2. **The reference repo our Pattern C mirrors —
   [`honestypugh2/foundry-copilot-search-validate`](https://github.com/honestypugh2/foundry-copilot-search-validate/blob/main/src/agents/orchestrator_pattern_b.py) —
   proves the same `file_metadata_lookup` tool definition inside a
   Foundry agent (Pattern B). This repo exposes it as a REST tool to
   Copilot Studio with **the same description text**, so the routing
   behaviour is consistent on both sides.
3. **Single-source vs multi-source.** Lab 2.4 demonstrates Foundry IQ
   over 3 knowledge sources (fraud patterns / regulations /
   procedures). Our Knowledge Base wraps a single index
   (`hr-policy-index`); to multi-source it, add additional
   `KnowledgeSource` entries in `create_foundry_agent.py` —
   `KnowledgeBase` already supports a list. The lab is the canonical
   example for that extension.

---

## Quick coverage matrix

| Lab  | Topic                                | Covered by             | Doc                                                                  |
| ---- | ------------------------------------ | ---------------------- | -------------------------------------------------------------------- |
| 1.4  | AI Search as Knowledge Source         | **Pattern A**          | [CopilotStudioIntegration.md](CopilotStudioIntegration.md)            |
| 2.1  | Knowledge Source                      | **Pattern A**          | [CopilotStudioIntegration.md](CopilotStudioIntegration.md)            |
| 2.1  | Custom HTTP flow                      | **Pattern C** (REST API) | [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md)        |
| 2.1  | Custom Connector                      | **Pattern C** (Swagger)  | [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json) |
| 2.1  | Advanced index design (HNSW, semantic, hybrid) | infra + indexing | [DataPipelineAndTesting.md](DataPipelineAndTesting.md)               |
| 2.3  | SharePoint indexer                    | Logic Apps alternative | [SharePointLogicAppsArchitecture.md](SharePointLogicAppsArchitecture.md) |
| 2.4  | Foundry IQ Knowledge Base + MCP agent | **Pattern B**          | [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md)           |
| 2.4  | Connected Agents (quick vs deep)      | **Pattern C** + A or B  | [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md)        |

---

## See Also

- [RetrievalPatterns.md](RetrievalPatterns.md) — the four patterns in detail
- [CopilotStudioIntegration.md](CopilotStudioIntegration.md) — wiring guide
- [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) — Pattern C and the trade-off vs native citations
- [Azure/Copilot-Studio-and-Azure](https://github.com/Azure/Copilot-Studio-and-Azure) — the upstream lab series
