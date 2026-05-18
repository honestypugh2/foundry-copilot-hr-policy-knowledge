# Architecture Options: Copilot Studio Search Patterns

Two patterns for improving Copilot Studio search with Azure AI Search, each sharing the same `src/config/search_config.json` for consistent index schema, synonym maps, semantic ranking, and category metadata.

> **See also:** [DataPipelineAndTesting.md](DataPipelineAndTesting.md) for detailed documentation on data ingestion, pre-processing stages, each script, and the testing strategy.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HR Policy Documents                                    │
│                                                                                  │
│  data/knowledge_base/ASK HR Knowledge/   OR   SharePoint Online Library          │
└─────────────────────┬──────────────────────────────┬────────────────────────────┘
                      │                              │
         ┌────────────┘                              └─────────────┐
         │                                                         │
         ▼                                                         ▼
┌─────────────────────────────┐                   ┌─────────────────────────────┐
│   Pattern 1: Option 1       │                   │   Pattern 1: Option 2       │
│   DocIntel + Client-Side    │                   │   Integrated Vectorization  │
│   Chunking + Push           │                   │   + Document Layout Skill   │
│                             │                   │                             │
│ • Azure Document Intel.     │                   │ • Blob Storage upload       │
│ • fixed_size_chunking()     │                   │ • DocIntel Layout Skill     │
│ • Client-side embeddings    │                   │ • Structure-aware chunking  │
│ • Push API to index         │                   │ • Server-side embeddings    │
│                             │                   │ • Indexer auto-processes    │
└────────────┬────────────────┘                   └────────────┬────────────────┘
             │                                                  │
             └──────────────────────┬───────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────────┐
                    │       Azure AI Search              │
                    │       hr-policy-index              │
                    │                                    │
                    │  • Hybrid: text + vector + semantic│
                    │  • Synonym map: hr-glossary        │
                    │  • Semantic config: hr-semantic    │
                    │  • Parent-child (index projections)│
                    │  • HNSW + scalar quantization      │
                    └───────────┬────────────┬──────────┘
                                │            │
                   ┌────────────┘            └────────────┐
                   │                                      │
                   ▼                                      ▼
    ┌──────────────────────────────┐     ┌──────────────────────────────┐
    │  Pattern 1: Knowledge Source │     │  Pattern 2: Foundry Agent    │
    │  (Direct)                    │     │  Action                      │
    │                              │     │                              │
    │  Copilot Studio connects     │     │  Copilot Studio invokes      │
    │  directly to AI Search       │     │  Foundry Agent via Action    │
    │  as a Knowledge Source       │     │                              │
    │                              │     │  • Knowledge Base (Foundry IQ│
    │  • Generative orchestration  │     │  • Agentic retrieval         │
    │  • Vector + semantic ranker  │     │  • MCP tool connection       │
    │  • Synonym map expansion     │     │  • Custom instructions       │
    │  • Automatic grounding       │     │  • Source attribution        │
    └──────────────────────────────┘     └──────────────────────────────┘
```

---

## Shared Configuration: `src/config/search_config.json`

Both patterns and all preprocessing options share the same configuration file. This ensures:

| Aspect | Shared Config Key | Purpose |
|---|---|---|
| **Index schema** | `search_config.index_name` | Same index `hr-policy-index` across all patterns |
| **Synonym map** | `synonym_map.name` | HR glossary synonyms (PTO→Paid Time Off, etc.) |
| **Semantic ranking** | `semantic_search.configuration_name` | `hr-semantic-config` with BM25 + semantic reranker |
| **Vector search** | `vector_search.vectorizer` | HNSW algorithm, scalar quantization, text-embedding-3-small |
| **Category metadata** | `search_config.policy_number_field` | Policy number, parent title, category fields |
| **Agentic retrieval** | `agentic_retrieval` | Knowledge Base/Source config for Pattern 2 |

The Python accessor module `src/config/search_config.py` provides typed access:

```python
from src.config.search_config import search_cfg

index_name = search_cfg.index_name          # "hr-policy-index"
synonym_map = search_cfg.synonym_map_name   # "hr-glossary-synonyms"
kb_name = search_cfg.knowledge_base_name    # "hr-knowledge-base"
```

---

## Pattern 1: Advanced Querying — Copilot Studio + Azure AI Search Knowledge Source (Direct)

Copilot Studio connects to `hr-policy-index` as a **Knowledge Source** with generative orchestration. The search index handles all retrieval (vector + semantic + synonym expansion).

### Option 1: Document Intelligence + Client-Side Chunking

**Script:** `scripts/index_knowledge_base_docintel_chunking.py`

```
Documents → Azure Document Intelligence (prebuilt-layout)
         → fixed_size_chunking (2000 chars, 200 overlap)
         → Glossary enrichment (HR_GLOSSARY)
         → Client-side embedding (text-embedding-3-small)
         → Push API → hr-policy-index
```

| Step | Component | Details |
|---|---|---|
| **Extract** | Azure Document Intelligence | `prebuilt-layout` model; fallback to python-docx / antiword |
| **Chunk** | `fixed_size_chunking()` | 2000 chars per chunk, 200-char overlap (configurable in `skillset.skills[0]`) |
| **Enrich** | `enrich_content_with_glossary()` | Appends matched HR_GLOSSARY terms for keyword boost |
| **Embed** | Azure OpenAI | `text-embedding-3-small`, 1536 dimensions |
| **Index** | Push API | Parent-child: `id` (chunk), `policy_parent_id` (parent) |

**When to use:**
- Full control over extraction and chunking logic
- Need to run locally or in CI/CD pipelines
- Custom preprocessing (glossary enrichment, category tagging)
- One-time or batch reindexing

**Usage:**
```bash
python scripts/index_knowledge_base_docintel_chunking.py
python scripts/index_knowledge_base_docintel_chunking.py --local-only    # test without Azure
python scripts/index_knowledge_base_docintel_chunking.py --data-dir data/knowledge_base_lab
```

### Option 2: Integrated Vectorization with Document Intelligence Layout Skill

**Script:** `scripts/index_knowledge_base_integrated_vectorization.py`

```
Documents → Azure Blob Storage
         → Azure AI Search Indexer
           ├─ DocumentIntelligenceLayoutSkill (structure-aware chunking)
           ├─ AzureOpenAIEmbeddingSkill (vectorization)
           └─ Index projections (parent-child mapping)
         → hr-policy-index
```

| Step | Component | Details |
|---|---|---|
| **Upload** | Azure Blob Storage | `ask-hr-knowledge` container |
| **Extract + Chunk** | Document Intelligence Layout Skill | Structure-aware: respects headings, paragraphs, tables; text output with 2000-char chunks, 200-char overlap |
| **Embed** | AzureOpenAIEmbeddingSkill | Server-side, `text-embedding-3-small`, 1536 dims |
| **Index** | Index projections | `skipIndexingParentDocuments`, parent-child via `policy_parent_id` |
| **Refresh** | Indexer change tracking | Automatic reprocessing when blob content changes |

**Pipeline components:**
- **Data source:** `hr-policy-index-blob-ds` (Azure Blob)
- **Skillset:** `hr-policy-doc-layout-skillset`
  - `DocumentIntelligenceLayoutSkill` — outputMode: oneToMany, outputFormat: text, chunkingProperties: {max: 2000, overlap: 200}
  - `AzureOpenAIEmbeddingSkill` — context: `/document/text_sections/*`
- **Index projections:** sourceContext: `/document/text_sections/*`, projectionMode: `skipIndexingParentDocuments`
- **Indexer:** `hr-policy-index-indexer` with `allowSkillsetToReadFileData: true`, `parsingMode: default`

**When to use:**
- Automated, production-grade ingestion
- Documents change frequently (auto-reindex)
- Want structure-aware semantic chunking (not fixed-size)
- Minimal code maintenance

**Usage:**
```bash
python scripts/index_knowledge_base_integrated_vectorization.py
python scripts/index_knowledge_base_integrated_vectorization.py --upload-only
python scripts/index_knowledge_base_integrated_vectorization.py --create-pipeline-only
```

### Option 1 vs Option 2 Comparison

| Aspect | Option 1: DocIntel + Chunking | Option 2: Integrated Vectorization |
|---|---|---|
| **Chunking** | Fixed-size (2000 chars, 200 overlap) | Structure-aware (headings, paragraphs) |
| **Embedding** | Client-side (Azure OpenAI SDK) | Server-side (AzureOpenAIEmbeddingSkill) |
| **Data freshness** | Manual re-run required | Automatic via indexer change tracking |
| **Extraction** | Azure DI prebuilt-layout API | Document Intelligence Layout Skill |
| **Deployment** | Script execution | Azure-managed pipeline |
| **Glossary enrichment** | Client-side (HR_GLOSSARY append) | Synonym map at index level |
| **Parent-child** | Push API with generated IDs | Index projections (native) |
| **Best for** | Dev/test, custom preprocessing | Production, automated ingestion |

### Parent-Child Chunking (Both Options)

Both options use the recommended single-index parent-child pattern:

```
┌─────────────────────────────────────────────────────┐
│  hr-policy-index (single index)                      │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ chunk_001    │  │ chunk_002    │  │ chunk_003    │  │
│  │ parent_id: A │  │ parent_id: A │  │ parent_id: B │  │
│  │ title: 50715 │  │ title: 50715 │  │ title: 51350 │  │
│  │ policy: ...  │  │ policy: ...  │  │ policy: ...  │  │
│  │ vector: [..] │  │ vector: [..] │  │ vector: [..] │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
```

- **Parent fields repeat** for each chunk (title, policy_number, category)
- **projectionMode:** `skipIndexingParentDocuments` (no null-chunk docs)
- **parent_key_field:** `policy_parent_id` links chunks to their source document

Reference: [Define an index projection for parent-child indexing](https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections)

---

## Pattern 2: Foundry Agent Action — Copilot Studio + Foundry IQ Agentic Retrieval

**Script:** `scripts/create_foundry_agent.py`

Copilot Studio invokes a **Foundry Agent** as an Action. The agent uses an MCP tool connected to a **Knowledge Base** (Foundry IQ) that wraps the same `hr-policy-index`. Foundry IQ provides agentic retrieval — AI-planned query routing and synthesis.

```
Copilot Studio → Foundry Agent Action → Foundry Agent (gpt-4o)
                                         │
                                         ├─ MCP Tool: knowledge_base_retrieve
                                         │   └─ Knowledge Base: hr-knowledge-base
                                         │       └─ Knowledge Source: hr-knowledge-source
                                         │           └─ Azure AI Search: hr-policy-index
                                         │
                                         └─ Answer with citations + source attribution
```

### Setup Steps

| Step | Script Function | What It Creates |
|---|---|---|
| 1 | `create_knowledge_source()` | `hr-knowledge-source` → points to `hr-policy-index` |
| 2 | `create_knowledge_base()` | `hr-knowledge-base` → wraps knowledge source(s) |
| 3 | `create_mcp_connection()` | MCP connection in Foundry project (managed identity) |
| 4 | `create_foundry_agent()` | `HRPolicyAgent` with `knowledge_base_retrieve` tool |

### Foundry IQ Capabilities

- **Agentic retrieval:** AI plans, searches, and synthesizes across sources
- **Automatic source routing:** Queries go to the right knowledge source(s)
- **Multi-source aggregation:** Complex queries span multiple sources
- **Source attribution:** Responses include which source provided each fact
- **Custom instructions:** Retrieval + answer instructions in search_config.json

### RBAC Requirements

| Role | Assigned To | Purpose |
|---|---|---|
| Search Index Data Contributor | Your user identity | Create indexes, upload documents |
| Search Index Data Reader | User + Project Managed Identity | Query indexes, access knowledge base |
| Search Service Contributor | Your user identity | Create knowledge bases and sources |

### Usage

```bash
# Full setup (requires index to be populated first via Pattern 1)
python scripts/create_foundry_agent.py

# Verify all resources exist
python scripts/create_foundry_agent.py --verify-only

# Cleanup Foundry IQ resources
python scripts/create_foundry_agent.py --cleanup
```

### Copilot Studio Integration

1. In Copilot Studio, add a **Foundry Agent Action**
2. Connect to agent `HRPolicyAgent` with the created version
3. Create a topic that invokes the agent action on user questions
4. The agent automatically searches the knowledge base and returns grounded answers with citations
5. Publish to Teams / Web Chat

Reference: [Foundry IQ Agents Lab](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.4-microsoft-foundry-agentic-retrieval/notebooks/foundry-IQ-agents.ipynb)

---

## Pattern 1 vs Pattern 2 Comparison

| Aspect | Pattern 1: Knowledge Source (Direct) | Pattern 2: Foundry Agent Action |
|---|---|---|
| **Copilot Studio config** | Knowledge Source → AI Search | Action → Foundry Agent |
| **Query handling** | Copilot Studio generative mode | Agent with MCP tool |
| **Retrieval intelligence** | Vector + semantic + synonym | Agentic: AI-planned routing + synthesis |
| **Multi-source** | Single index per Knowledge Source | Multiple knowledge sources in one KB |
| **Custom instructions** | Limited (Copilot Studio settings) | Full agent instructions + retrieval/answer guidance |
| **Source attribution** | Basic (Copilot Studio citations) | Rich (per-fact source attribution) |
| **Latency** | Lower (direct search) | Higher (agent reasoning + tool call) |
| **Complexity** | Simpler setup | Requires Foundry project + RBAC |
| **Best for** | Simple Q&A, fast responses | Complex queries, multi-source, detailed citations |

---

## Production: SharePoint + Logic Apps Integration

For production environments where HR policies live in SharePoint:

```
SharePoint Online → Logic Apps → Document Intelligence → Azure AI Search → Copilot Studio
```

See [SharePointLogicAppsArchitecture.md](SharePointLogicAppsArchitecture.md) for the full production workflow including:
- SharePoint trigger configuration
- Document Intelligence processing in Logic Apps
- Chunking strategies (paragraph-level, page-level, sliding window)
- Metadata enrichment (site, library, ACL hints)
- Push API vs Integrated Vectorization indexing options

Both Pattern 1 and Pattern 2 work with the Logic Apps pipeline — the pipeline populates the same `hr-policy-index` that both patterns consume.

---

## Scripts Summary

| Script | Pattern | Purpose |
|---|---|---|
| `scripts/index_knowledge_base_docintel_chunking.py` | Pattern 1, Option 1 | DocIntel extraction → fixed-size chunking → client embedding → push to index |
| `scripts/index_knowledge_base_integrated_vectorization.py` | Pattern 1, Option 2 | Upload to blob → Document Layout Skill → server embedding → indexer pipeline |
| `scripts/create_foundry_agent.py` | Pattern 2 | Create Knowledge Source → Knowledge Base → MCP connection → Foundry Agent |
| `scripts/index_knowledge_base.py` | Legacy (deprecated) | Original indexing script (whole document, no chunking) |
| `scripts/index_knowledge_base_chunking.py` | Legacy (deprecated) | Original chunking script (fixed-size, client-side) |
| `scripts/upload_to_blob.py` | Shared | Upload raw documents to Azure Blob Storage |

## Shared Modules

| Module | Used By | Purpose |
|---|---|---|
| `src/config/search_config.json` | All patterns | Index schema, synonym maps, semantic config, skillsets, agentic retrieval |
| `src/config/search_config.py` | All patterns | Python accessor for search_config.json |
| `src/search/integrated_vectorization_search.py` | Pattern 1 (both options) | Search client for hybrid queries (text + vector + semantic) |
| `src/search/search_service.py` | All patterns | HR_GLOSSARY, expand_query_with_glossary(), legacy search client |
| `src/document_processing/document_ingestion.py` | Pattern 1, Option 1 | Azure Document Intelligence text extraction |
| `src/document_processing/chunking.py` | Pattern 1, Option 1 | fixed_size_chunking() with overlap |

---

## Environment Variables

```bash
# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<api-key>                    # or use managed identity
AZURE_SEARCH_INDEX_NAME=hr-policy-index
USE_MANAGED_IDENTITY=true

# Azure OpenAI (embeddings + LLM)
AZURE_OPENAI_ENDPOINT=https://<region>.openai.azure.com/
AZURE_OPENAI_API_KEY=<api-key>                    # or use managed identity

# Azure Document Intelligence (Pattern 1, Option 1)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<region>.api.cognitive.microsoft.com/

# Azure Blob Storage (Pattern 1, Option 2)
AZURE_STORAGE_CONNECTION_STRING=<connection-string>
AZURE_STORAGE_ACCOUNT_URL=https://<storage>.blob.core.windows.net/

# Azure AI Foundry (Pattern 2)
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com
AI_FOUNDRY_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com
PROJECT_RESOURCE_ID=/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.MachineLearningServices/workspaces/<project>

# Azure AI Services (Document Layout Skill billing)
AZURE_AI_SERVICES_KEY=<cognitive-services-key>

# Copilot Studio
COPILOT_STUDIO_ENVIRONMENT_ID=<env-id>
COPILOT_STUDIO_AGENT_SCHEMA=<schema-name>
```

---

## References

- [Copilot Studio — Azure AI Search as Knowledge](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)
- [Document Intelligence Layout Skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-document-intelligence-layout)
- [Semantic Chunking](https://learn.microsoft.com/en-us/azure/search/search-how-to-semantic-chunking)
- [Index Projections (Parent-Child)](https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections)
- [Foundry IQ — Agentic Retrieval](https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.4-microsoft-foundry-agentic-retrieval/notebooks/foundry-IQ-agents.ipynb)
- [Azure AI Search — Integrated Vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [SharePoint + Logic Apps Architecture](SharePointLogicAppsArchitecture.md)
