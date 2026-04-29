# HR Policy Knowledge Agent

> **Ask HR** — An AI-powered assistant that answers employee questions using internal HR policy documents, built with Azure AI Foundry, Azure AI Search, Microsoft Agent Framework, and Copilot Studio.

## Overview

This demo showcases a Retrieval-Augmented Generation (RAG) solution for HR policy Q&A. Employees ask questions in natural language — including informal shorthand — and receive grounded answers with specific policy citations.

### Customer Challenges Addressed

| # | Challenge | Solution |
|---|---|---|
| 1 | **Incorrect grounding** against authoritative data | Agent instructions enforce citing specific policy numbers; answers restricted to retrieved documents |
| 2 | **Difficulty understanding technician vernacular** | HR glossary maps ~30 informal terms to formal policy names before search |
| 3 | **Managing multiple data sources** in a single agent | Sub-agent / sequential workflow pattern handles different policy categories |
| 4 | **Prompt and instruction limitations** in Copilot Studio | Detailed agent instructions with 7 grounding rules in the backend |

## Architecture

This project supports two architecture options. **Copilot Studio** is the recommended default — it connects directly to Azure AI Search with no custom backend required. A **FastAPI + React** alternative is also included for advanced scenarios that need full orchestration control.

### Option A: Copilot Studio (Recommended)

```
Employee (Teams / Web Chat)
          │
          ▼
    Copilot Studio
          │
          ▼
  Azure AI Search
  (hr-policy-index)
          │
          ▼
  Grounded HR Answer
```

Copilot Studio queries the Azure AI Search index directly using **text search + semantic ranker**. No custom backend is required. Vernacular handling is provided by an index-level synonym map.

### Option B: FastAPI + React (Advanced)

```
  React Frontend
        │
        ▼
  FastAPI Backend
        │
  ┌─────┼─────┐
  ▼     ▼     ▼
Query Policy  Answer
Understand Retrieval Generation
(Glossary) (AI Search) (RAG + LLM)
```

The FastAPI backend adds capabilities beyond what Copilot Studio provides natively:
- **Hybrid search** (text + vector) via `content_vector` embeddings
- **Python-side glossary expansion** on top of the index synonym map
- **Sequential workflow orchestration** using Microsoft Agent Framework
- **Structured citations** with policy numbers and confidence scores

See [docs/Architecture.md](docs/Architecture.md) for the full diagram.

## Tech Stack

| Component | Technology | Used By |
|---|---|---|
| Azure AI Search | Full-text + semantic search with HR glossary | Both options |
| Azure AI Search (Integrated Vectorization) | Indexer + skillset pipeline with server-side chunking and embedding | Option B (default), Option A (with vectorizer) |
| Azure Document Intelligence | Word document extraction | Both options |
| Azure OpenAI (GPT-4o) | Answer generation | Both options |
| Azure AI Foundry | `azure-ai-projects>=2.0.0` | Option B |
| Microsoft Agent Framework | Sequential workflows (`agent-framework --pre`) | Option B |
| Copilot Studio | Teams / web chat interface | Option A |
| FastAPI | REST API backend | Option B |
| React + TypeScript + Vite | Chat UI (`src/frontend`, `src/frontend-copilot-studio`) | Option B |

### Search Modes

The project supports two search modes:

| Mode | Description | Default |
|---|---|---|
| **Integrated Vectorization** | Azure AI Search indexer + skillset pipeline handles chunking and embedding at index time. Query-time embedding via AzureOpenAI vectorizer. Config: `src/config/search_config.json` | Yes |
| **Legacy** | Client-side chunking and embedding via `scripts/index_knowledge_base.py`. Query-time embedding generated client-side. | No |

Set `SEARCH_MODE=legacy` in your environment to use the legacy search mode. See [docs/Architecture.md](docs/Architecture.md) for details.

## Quick Start — Option A: Copilot Studio

### Prerequisites

- Azure subscription with AI Search, OpenAI, and Document Intelligence
- Azure CLI (`az login`)
- Python 3.10+ and [uv](https://docs.astral.sh/uv/) (for indexing scripts)
- Copilot Studio license (Power Virtual Agents)

### 1. Clone and Setup

```bash
git clone https://github.com/honestypugh2/foundry-copilot-hr-policy-knowledge.git
cd foundry-copilot-hr-policy-knowledge
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Azure credentials:

```bash
cp .env.example .env
# Edit .env with your Azure service endpoints and keys
```

### 3. Index the Knowledge Base

Process the HR policy Word documents and upload to Azure AI Search:

```bash
uv run python -m scripts.index_knowledge_base
```

For local-only processing (no Azure services):
```bash
uv run python -m scripts.index_knowledge_base --local-only
```

### 4. Set Up Copilot Studio

Connect Copilot Studio to your Azure AI Search index by following the step-by-step guide:

> **[Copilot Studio Integration Guide](docs/CopilotStudioIntegration.md)**

The guide covers:
- Creating a Copilot in Copilot Studio
- Adding Azure AI Search as a knowledge source
- Configuring agent instructions and generative AI settings
- Setting up vernacular handling via synonym maps
- Publishing to Microsoft Teams
- Testing and troubleshooting

After completing these steps, employees can ask HR questions directly from Teams or the Copilot Studio web chat — no backend deployment needed.

---

## Quick Start — Option B: FastAPI + React

Use this option when you need hybrid vector search, the full Agent Framework orchestration pipeline, or a custom React UI.

### Additional Prerequisites

- Node.js 18+

### 1–3. Same as Option A

Follow steps 1–3 above to clone, configure, and index the knowledge base.

### 4. Start the Backend

```bash
uv run python -m src.backend.main
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 5. Start a Frontend

**Agent Framework frontend:**
```bash
cd src/frontend
npm install && npm run dev
# http://localhost:5173
```

**Copilot Studio Web Chat embed frontend:**
```bash
cd src/frontend-copilot-studio
npm install && npm run dev
# http://localhost:5174
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Submit an HR question, get a grounded answer |
| `GET` | `/api/health` | Health check for all Azure services |
| `GET` | `/api/knowledge-base` | Knowledge base metadata and file list |
| `POST` | `/api/knowledge-base/reindex` | Trigger re-indexing of all documents |
| `POST` | `/api/documents/upload` | Upload and index a new HR document |
| `GET` | `/api/glossary` | HR vernacular-to-formal term glossary |
| `GET` | `/api/azure/status` | Azure service configuration status |
| `GET` | `/api/copilot-studio/token` | Direct Line token for Copilot Studio Web Chat |
| `POST` | `/api/copilot-studio/chat` | Proxy chat to Copilot Studio agent |
| `GET` | `/api/copilot-studio/config` | Copilot Studio configuration status |

---

## Project Structure

```
├── src/
│   ├── agents/
│   │   ├── hr_policy_agent.py     # RAG agent with grounding rules
│   │   └── orchestrator.py        # Sequential workflow (WorkflowBuilder)
│   ├── backend/
│   │   └── main.py                # FastAPI application (Option B)
│   ├── document_processing/
│   │   └── document_ingestion.py  # Doc Intelligence + python-docx
│   ├── search/
│   │   ├── search_service.py      # AI Search + HR glossary (legacy)
│   │   └── integrated_vectorization_search.py  # Integrated vectorization search (default)
│   ├── config/
│   │   └── search_config.json     # Search index, vector, and semantic config
│   ├── models/
│   │   └── schemas.py             # Pydantic data models
│   ├── copilot_studio/
│   │   └── service.py             # Direct-to-Engine API client
│   ├── frontend/                  # React chat UI (Option B)
│   └── frontend-copilot-studio/   # React + Copilot Studio Web Chat embed (Option B)
├── scripts/
│   ├── index_knowledge_base.py    # Batch indexing script
│   └── setup.sh                   # Project setup
├── data/knowledge_base/           # HR policy Word documents
├── docs/
│   ├── Architecture.md            # System architecture
│   └── CopilotStudioIntegration.md # Copilot Studio guide (Option A)
├── infra/
│   └── main.bicep                 # Azure infrastructure
└── tests/
```

## Running Tests

```bash
uv run pytest tests/ -v
```

## Infrastructure Deployment

Deploy all Azure resources using Bicep:

```bash
az deployment group create \
  --resource-group <your-rg> \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

## License

See [LICENSE](LICENSE).