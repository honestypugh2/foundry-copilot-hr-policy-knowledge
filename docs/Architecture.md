# Architecture Overview

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         Clients                                │
│                                                                │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │  Copilot Studio (Teams / Web Chat)                       │ │
│   │  Power Platform Environment                              │ │
│   └──────────────────────────┬───────────────────────────────┘ │
│                              │                                 │
└──────────────────────────────┼─────────────────────────────────┘
                               │  Azure AI Search
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                                                                │
│   ┌────────────────────────────────────────────────────────┐   │
│   │          Sequential Workflow Orchestrator               │   │
│   │          (Agent Framework WorkflowBuilder)              │   │
│   │                                                        │   │
│   │   ┌──────────────┐  ┌───────────────┐  ┌───────────┐  │   │
│   │   │    Query      │  │    Policy     │  │  Answer   │  │   │
│   │   │ Understanding │─►│  Retrieval   │─►│Generation │  │   │
│   │   │  (Glossary)   │  │ (AI Search)  │  │  (RAG)    │  │   │
│   │   └──────────────┘  └───────────────┘  └───────────┘  │   │
│   └────────────────────────────────────────────────────────┘   │
│                                                                │
└───────────┬──────────────────┬──────────────────┬──────────────┘
            │                  │                  │
            ▼                  ▼                  ▼
┌──────────────────┐ ┌─────────────────┐ ┌────────────────────┐
│  Azure AI Search │ │  Azure OpenAI   │ │  Azure Document    │
│  (hr-policy-     │ │  (gpt-4o)       │ │  Intelligence      │
│   index)         │ │                 │ │  (prebuilt-layout) │
└──────────────────┘ └─────────────────┘ └────────────────────┘
```

## Data Flow

### Document Ingestion
1. Word documents placed in `data/knowledge_base/ASK HR Knowledge/`
2. `scripts/index_knowledge_base.py` processes each document:
   - Azure Document Intelligence extracts text (or python-docx fallback)
   - Policy number, category, and metadata are extracted
   - Documents uploaded to Azure AI Search index

### Question Answering
1. User submits question via chat UI or Copilot Studio
2. **Query Understanding**: Glossary expands vernacular terms
3. **Policy Retrieval**: Azure AI Search finds relevant policies
4. **Answer Generation**: AI agent produces grounded answer with citations
5. Response includes answer, policy references, confidence score

## Key Components

| Component | Technology | Purpose |
|---|---|---|
| Chat Interface | Copilot Studio | Teams / web chat UI (primary) |
| Backend | FastAPI + Uvicorn | REST API, orchestration |
| Orchestrator | Agent Framework (WorkflowBuilder) | Sequential workflow |
| Search | Azure AI Search | Full-text + semantic search |
| Search (Integrated Vectorization) | Azure AI Search (indexer + skillset) | Hybrid search with server-side chunking and embedding |
| LLM | Azure OpenAI (gpt-4o) | Answer generation |
| Doc Processing | Azure Document Intelligence | Word doc extraction |

## Search Options

### Option 1: Legacy Search (HRPolicySearchService)

The original search mode. Documents are pre-processed and embedded client-side, then uploaded to the index. Queries use hybrid search (text + vector + semantic ranker) with client-side embedding generation.

- **Indexing**: Client-side chunking and embedding via `scripts/index_knowledge_base.py`
- **Query**: Client-side embedding + `VectorizedQuery` + semantic ranker
- **Fields**: `title`, `content`, `content_vector`, `policy_number`, `category`
- **Pros**: Full control over chunking and embedding, works without indexer/skillset
- **Cons**: Requires maintaining a separate embedding pipeline

### Option 2: Integrated Vectorization Search (IntegratedVectorizationSearchService)

Uses Azure AI Search's [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization) to handle chunking and embedding at index time via an indexer + skillset pipeline, and query-time embedding via an AzureOpenAI vectorizer.

- **Indexing**: Indexer pulls from Azure Blob Storage → SplitSkill chunks → AzureOpenAIEmbeddingSkill embeds → index
- **Query**: AzureOpenAI vectorizer converts text queries to vectors at query time + semantic ranker
- **Fields**: `snippet`, `snippet_vector`, `parent_title`, `policy_number`, `blob_url`
- **Config**: `src/config/search_config.json`
- **Pros**: No separate embedding pipeline, automatic reindexing on data changes, simpler maintenance
- **Cons**: Requires Azure AI Search indexer + skillset setup

The search mode defaults to integrated vectorization. Set `SEARCH_MODE=legacy` in your environment to use the original search service.

## Addressing Customer Challenges

| Challenge | Solution | Component |
|---|---|---|
| Incorrect grounding | Agent instructions enforce citation of specific policy numbers | `hr_policy_agent.py` |
| Vernacular difficulty | HR glossary maps ~30 informal terms to formal names | `search_service.py` |
| Multiple data sources | Sub-agent pattern with category-based routing | `orchestrator.py` |
| Prompt limitations | Detailed agent instructions with 7 grounding rules | `hr_policy_agent.py` |
