# SharePoint → Logic Apps → Document Intelligence → Azure AI Search → Copilot Studio

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        SharePoint Online                             │
│                                                                      │
│   HR Policy Library                                                  │
│   ┌────────────────────────────────────────────────────────┐         │
│   │  .docx / .pdf files created or modified                │         │
│   └──────────────────────────┬─────────────────────────────┘         │
│                              │  Trigger: file created / updated      │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Azure Logic Apps                                │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │  1. Trigger on SharePoint file event                        │    │
│   │  2. Get file content from SharePoint                        │    │
│   │  3. Call Azure AI Document Intelligence (Analyze)           │    │
│   │     ├─ prebuilt-layout / prebuilt-document / custom model   │    │
│   │     └─ Returns structured JSON + extracted text             │    │
│   │  4. Normalize + chunk content (paragraph / page level)      │    │
│   │  5. Attach metadata (site, library, doc type, ACL hints)    │    │
│   │  6. Push documents + vectors to Azure AI Search             │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Azure AI Search                                 │
│                                                                      │
│   Index: hr-policy-index                                             │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │  • Vector index (embeddings from integrated vectorization   │    │
│   │    or pre-computed embeddings pushed by Logic App)           │    │
│   │  • Semantic ranker enabled                                  │    │
│   │  • Synonym maps for HR vernacular                           │    │
│   │  • Fields: content, title, policy_number, category,         │    │
│   │    chunk_id, metadata, content_vector                       │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Copilot Studio Agent                           │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │  Knowledge Source: Azure AI Search (hr-policy-index)        │    │
│   │  Retrieval: vector + semantic ranker for grounded responses │    │
│   │  Channels: Microsoft Teams / Web Chat                       │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│   Employee asks HR question ──► Grounded answer with citations       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Workflow (Step-by-Step)

### Step 1 — Trigger from SharePoint

A Logic App **When a file is created or modified** trigger monitors one or more SharePoint document libraries (e.g., the *ASK HR Knowledge* library). Every time an HR team member publishes or updates a policy document, the Logic App fires automatically.

| Setting | Value |
|---|---|
| Trigger | `When a file is created or modified (properties only)` |
| Site Address | `https://<tenant>.sharepoint.com/sites/HRPolicies` |
| Library Name | `ASK HR Knowledge` |
| Folder | `/` (root or specific subfolder) |
| Check frequency | Every 1–5 minutes (configurable) |

**References**
- [SharePoint + Logic Apps trigger pattern](https://learn.microsoft.com/en-us/connectors/sharepointonline/#when-a-file-is-created-or-modified-(properties-only))
- [Azure-Samples: Logic Apps with SharePoint](https://github.com/Azure/logicapps)

### Step 2 — Document Intelligence Processing

The Logic App calls **Azure AI Document Intelligence** to extract structured content from the file.

| Option | Model ID | Best For |
|---|---|---|
| Layout extraction | `prebuilt-layout` | Tables, headings, paragraphs, page structure |
| General document | `prebuilt-document` | Key-value pairs, entities, full text |
| Custom model | `<custom-model-id>` | Domain-specific fields (policy number, effective date) |

The Analyze Document action returns:
- **Full extracted text** — concatenated page content
- **Structured JSON** — paragraphs, tables, and sections with bounding regions
- **Key-value pairs** (if using `prebuilt-document` or custom model)

```
Logic App Action: "Analyze Document"
────────────────────────────────
Input:  File content (binary) from SharePoint
Model:  prebuilt-layout  (recommended for HR policy docs)
Output: analyzeResult JSON
        ├─ content          (full text)
        ├─ pages[]          (per-page text + layout)
        ├─ tables[]         (structured table data)
        └─ paragraphs[]     (paragraph-level segments)
```

**References**
- [Document Intelligence layout model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-layout)
- [Call Document Intelligence from Logic Apps](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/how-to-guides/use-sdk-rest-api)

### Step 3 — Prepare AI Search Documents

Inside the same Logic App, a **Compose** + **Select** action pipeline transforms the Document Intelligence output into search-ready documents.

#### 3a. Chunking Strategy

| Strategy | Description | Recommended When |
|---|---|---|
| Paragraph-level | One search document per `paragraph` from the analyze result | Short policies, FAQ-style content |
| Page-level | One search document per `page` | Longer narrative policies |
| Sliding window | Fixed token-length chunks with overlap | Uniform chunk sizes needed for vector search |

#### 3b. Metadata Enrichment

Each chunk document is enriched with metadata extracted from SharePoint and the file itself:

```json
{
  "chunk_id": "<doc-id>_chunk_001",
  "content": "Extracted text for this chunk...",
  "title": "50715 - Hours Worked and Pay Administration: Holiday Pay",
  "policy_number": "50715",
  "category": "Hours Worked and Pay Administration",
  "source_library": "ASK HR Knowledge",
  "sharepoint_site": "https://<tenant>.sharepoint.com/sites/HRPolicies",
  "file_name": "50715 - Hours Worked and Pay Administration_ Holiday Pay.docx",
  "last_modified": "2026-02-15T10:30:00Z",
  "doc_type": "Policy",
  "acl_hints": ["All Employees"]
}
```

### Step 4 — Index into Azure AI Search

The Logic App pushes the prepared documents into the `hr-policy-index` using one of two approaches:

#### Option A: Push API (Pre-Chunked Documents)

The Logic App calls the **Azure AI Search Index Documents** REST action directly to upload the chunked documents assembled in Step 3.

```
POST https://<search-service>.search.windows.net/indexes/hr-policy-index/docs/index?api-version=2024-07-01
Content-Type: application/json
api-key: <admin-key>

{
  "value": [
    { "@search.action": "mergeOrUpload", "chunk_id": "...", "content": "...", ... },
    ...
  ]
}
```

If using pre-computed embeddings, generate vectors via an Azure OpenAI Embeddings call before pushing:

```
Logic App ──► Azure OpenAI (text-embedding-ada-002 / text-embedding-3-small)
          └─► Attach content_vector field to each chunk
          └─► Push to Azure AI Search
```

#### Option B: Integrated Vectorization

Azure AI Search **integrated vectorization** handles chunking and embedding automatically at index time. In this case the Logic App pushes full documents to a blob container, and an AI Search indexer with a skillset processes them.

```
Logic App ──► Azure Blob Storage (upload extracted text)
                      │
                      ▼
              AI Search Indexer
              ├─ Text split skill (chunking)
              ├─ Azure OpenAI embedding skill (vectorization)
              └─► hr-policy-index
```

**References**
- [Logic Apps RAG templates for AI Search](https://azure.github.io/LogicAppsTemplates/)
- [Azure AI Search integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Index Documents REST API](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/)

### Step 5 — Copilot Studio Consumes Azure AI Search

Copilot Studio connects to `hr-policy-index` as a **Knowledge** source and uses vector + semantic ranking to ground every response.

| Configuration | Value |
|---|---|
| Knowledge type | Azure AI Search |
| Search endpoint | `https://<search-service>.search.windows.net` |
| Index name | `hr-policy-index` |
| Authentication | API Key (query key) or Managed Identity |
| Content field | `content` |
| Title field | `title` |
| Retrieval mode | Vector + semantic ranker (hybrid) |

When an employee asks a question:
1. Copilot Studio converts the query into a vector embedding
2. Hybrid retrieval (vector similarity + BM25 keyword) runs against the index
3. Semantic ranker re-ranks the top results for relevance
4. Generative answers produce a grounded response with citations

See [CopilotStudioIntegration.md](CopilotStudioIntegration.md) for detailed Copilot Studio setup steps including publishing to Teams.

---

## Index Schema

```json
{
  "name": "hr-policy-index",
  "fields": [
    { "name": "chunk_id",        "type": "Edm.String",  "key": true,  "filterable": true  },
    { "name": "content",         "type": "Edm.String",  "searchable": true, "analyzer": "en.microsoft" },
    { "name": "content_vector",  "type": "Collection(Edm.Single)", "searchable": true,
      "dimensions": 1536, "vectorSearchProfile": "default-profile" },
    { "name": "title",           "type": "Edm.String",  "searchable": true, "filterable": true },
    { "name": "policy_number",   "type": "Edm.String",  "filterable": true, "sortable": true  },
    { "name": "category",        "type": "Edm.String",  "filterable": true, "facetable": true },
    { "name": "source_library",  "type": "Edm.String",  "filterable": true  },
    { "name": "sharepoint_site", "type": "Edm.String",  "filterable": true  },
    { "name": "file_name",       "type": "Edm.String",  "filterable": true  },
    { "name": "last_modified",   "type": "Edm.DateTimeOffset", "filterable": true, "sortable": true },
    { "name": "doc_type",        "type": "Edm.String",  "filterable": true, "facetable": true },
    { "name": "acl_hints",       "type": "Collection(Edm.String)", "filterable": true }
  ],
  "semantic": {
    "configurations": [{
      "name": "hr-semantic-config",
      "prioritizedFields": {
        "titleField": { "fieldName": "title" },
        "contentFields": [{ "fieldName": "content" }]
      }
    }]
  }
}
```

## Azure Resources Required

| Resource | SKU / Tier | Purpose |
|---|---|---|
| SharePoint Online | Microsoft 365 E3/E5 | Source document library |
| Azure Logic Apps | Consumption or Standard | Orchestration (trigger → process → index) |
| Azure AI Document Intelligence | S0 | Document extraction |
| Azure OpenAI | S0 | Embeddings (`text-embedding-3-small`) |
| Azure AI Search | Basic or Standard (S1+) | Vector + semantic index |
| Copilot Studio | Per-user or per-tenant license | Employee-facing chat agent |
| Azure Blob Storage *(optional)* | Standard LRS | Intermediate storage for integrated vectorization |

## Comparison with the Agent Framework Architecture

This project ships two architectural paths. Choose based on your requirements:

| Aspect | Logic Apps Pipeline (this doc) | Agent Framework Backend ([Architecture.md](Architecture.md)) |
|---|---|---|
| **Ingestion** | Automated via SharePoint trigger | Manual script (`index_knowledge_base.py`) |
| **Orchestration** | Azure Logic Apps (low-code) | FastAPI + WorkflowBuilder (code-first) |
| **Processing** | Document Intelligence (in Logic App) | Document Intelligence or python-docx fallback |
| **Vectorization** | Integrated vectorization or pre-push | Pre-push via indexing script |
| **Query handling** | Copilot Studio (generative answers) | Sequential agent workflow (glossary → search → RAG) |
| **Vernacular support** | Synonym maps in AI Search | Glossary expansion in backend |
| **Best for** | Fully automated, low-code, Teams-first | Custom logic, multi-source, advanced orchestration |

Both architectures share the same Azure AI Search index (`hr-policy-index`), so they can coexist — the Logic Apps pipeline keeps the index current while the Agent Framework backend provides advanced query capabilities.

## References

- [SharePoint connector — When a file is created or modified](https://learn.microsoft.com/en-us/connectors/sharepointonline/)
- [Azure AI Document Intelligence — Layout model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-layout)
- [Azure AI Document Intelligence — Prebuilt document model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-general-document)
- [Logic Apps RAG templates](https://github.com/Azure/logicapps/tree/master/LogicApps-AI-RAG-Demo)
- [Azure AI Search — Integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Azure AI Search — Semantic ranking](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview)
- [Copilot Studio — Azure AI Search as knowledge](https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search)
