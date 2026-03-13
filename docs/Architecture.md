# Architecture Overview

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         Clients                                │
│                                                                │
│   ┌─────────────────┐    ┌──────────────────────────────────┐  │
│   │  React Frontend  │    │  Copilot Studio (Teams / Web)    │  │
│   │  (Vite + TS)     │    │  Power Platform Environment      │  │
│   └────────┬─────────┘    └──────────────┬───────────────────┘  │
│            │                             │                      │
└────────────┼─────────────────────────────┼──────────────────────┘
             │  /api/*                     │  Azure AI Search
             ▼                             ▼
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
| Frontend | React + TypeScript + Vite | Chat UI, KB browser |
| Backend | FastAPI + Uvicorn | REST API, orchestration |
| Orchestrator | Agent Framework (WorkflowBuilder) | Sequential workflow |
| Search | Azure AI Search | Full-text + semantic search |
| LLM | Azure OpenAI (gpt-4o) | Answer generation |
| Doc Processing | Azure Document Intelligence | Word doc extraction |
| Chat Interface | Copilot Studio | Teams integration |

## Addressing Customer Challenges

| Challenge | Solution | Component |
|---|---|---|
| Incorrect grounding | Agent instructions enforce citation of specific policy numbers | `hr_policy_agent.py` |
| Vernacular difficulty | HR glossary maps ~30 informal terms to formal names | `search_service.py` |
| Multiple data sources | Sub-agent pattern with category-based routing | `orchestrator.py` |
| Prompt limitations | Detailed agent instructions with 7 grounding rules | `hr_policy_agent.py` |
