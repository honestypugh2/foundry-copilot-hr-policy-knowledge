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

Copilot Studio supports **two integration paths** to the same `hr-policy-index`:

```
Employee (Teams / Web Chat)
          │
          ▼
    Copilot Studio
          │
    ┌─────┴─────┐
    ▼            ▼
  Path 1       Path 2
  Knowledge    Foundry Agent
  Source       Action
  (Direct)     (Agentic Retrieval)
    │            │
    ▼            ▼
  Azure AI     Foundry Agent (gpt-4o)
  Search         │
  (hr-policy-    ├─ MCP Tool: knowledge_base_retrieve
   index)        │   └─ Knowledge Base → hr-policy-index
    │            │
    ▼            ▼
  Grounded HR Policy Answer
```

| Path | How It Works | Best For |
|------|-------------|----------|
| **Path 1: Knowledge Source (Direct)** | Copilot Studio queries `hr-policy-index` directly via its native Azure AI Search connector. Supports text + vector (integrated vectorization) + semantic ranker. Copilot Studio's built-in LLM synthesizes the answer. | Simple Q&A, fast responses, quick setup |
| **Path 2: Foundry Agent Action** | Copilot Studio invokes a Foundry Agent as an Action. The agent uses agentic retrieval (Foundry IQ) for AI-planned query routing, subquery decomposition, and source attribution. Custom retrieval + answer instructions. | Complex queries, multi-source, detailed citations, grounded reasoning |

Both paths share the same index — populate it once using either indexing option, then configure one or both paths in Copilot Studio.

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
| Azure AI Foundry | `azure-ai-projects>=2.0.0` | Option A Path 2, Option B |
| Microsoft Agent Framework | `agent-framework>=1.1.1`, `agent-framework-foundry>=1.1.1` | Option A Path 2, Option B |
| Copilot Studio | Teams / web chat interface | Option A (both paths) |
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

Two indexing options are available. Pick one based on your needs (see [Scripts Reference](#scripts-reference) for full details):

**Option 1 — Client-side chunking (recommended for dev/test):**
```bash
uv run python scripts/index_knowledge_base_docintel_chunking.py
```

**Option 2 — Integrated vectorization (recommended for production):**
```bash
# Upload documents to Blob Storage, then create the indexer pipeline
uv run python scripts/index_knowledge_base_integrated_vectorization.py
```

For local-only extraction testing (no Azure Search upload):
```bash
uv run python scripts/index_knowledge_base_docintel_chunking.py --local-only
```

### 4. Set Up Copilot Studio

Choose one or both integration paths:

#### Path 1: Azure AI Search as Knowledge Source (Quick Setup)

Connect Copilot Studio directly to your search index — no backend or Foundry project needed.

1. In Copilot Studio, create a new copilot (`Ask HR Policy Agent`)
2. Go to **Knowledge** → **Add knowledge** → **Azure AI Search**
3. Create a connection with your search endpoint + API key
4. Enter index name: `hr-policy-index` → **Add to agent**
5. Configure agent instructions on the **Overview** page (see [CopilotStudioIntegration.md](docs/CopilotStudioIntegration.md#step-3-configure-agent-instructions-and-generative-ai-settings))
6. Turn off "Allow the AI to use its own general knowledge" under **Settings → Generative AI**
7. Publish to Teams

> Copilot Studio automatically leverages the semantic ranker and integrated vectorization vectorizer when available on the index.

#### Path 2: Foundry Agent Action (Agentic Retrieval)

Wrap the search index in a Foundry Knowledge Base and expose it as an agent action in Copilot Studio.

1. **Create the Foundry Agent** (requires index to be populated from step 3):
   ```bash
   uv run python scripts/create_foundry_agent.py
   ```
   This creates: Knowledge Source → Knowledge Base → MCP connection → Foundry Agent (`HRPolicyAgent`, gpt-4o) with `knowledge_base_retrieve` tool.

2. **Connect in Copilot Studio:**
   - Go to **Tools** → **Add a tool** → **Azure AI Foundry agent**
   - Select your AI Foundry project and the `HRPolicyAgent`
   - The Foundry agent runs as a sub-agent with agentic retrieval (AI-planned query routing, subquery decomposition, semantic ranking, and answer synthesis)

3. **Alternative — REST API Tool:** If your Foundry Agent is deployed as an API (e.g., Azure Function), you can also add it as a REST API tool using an OpenAPI spec. See [CopilotStudioIntegration.md](docs/CopilotStudioIntegration.md) for details.

> **RBAC required:** The Foundry project's managed identity needs `Search Index Data Reader` on the search service. See [docs/ArchitectureOptions.md](docs/ArchitectureOptions.md#rbac-requirements).

#### Full Guide

> **[Copilot Studio Integration Guide](docs/CopilotStudioIntegration.md)**

The guide covers both paths in detail:
- Creating a Copilot in Copilot Studio
- Path 1: Adding Azure AI Search as a knowledge source
- Path 2: Adding a Foundry Agent Action (direct or via REST API tool)
- Configuring agent instructions and generative AI settings
- Setting up vernacular handling via synonym maps
- Publishing to Microsoft Teams
- Testing and troubleshooting

After completing these steps, employees can ask HR questions directly from Teams or the Copilot Studio web chat — no custom backend deployment needed.

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
│   │   ├── hr_policy_agent.py     # RAG agent (FoundryChatClient + Agent Framework SDK)
│   │   └── orchestrator.py        # Sequential workflow (SequentialBuilder pipeline)
│   ├── backend/
│   │   └── main.py                # FastAPI application (Option B)
│   ├── config/
│   │   ├── search_config.json     # Shared index schema, vector, semantic, skillset config
│   │   └── search_config.py       # Typed Python accessor for search_config.json
│   ├── document_processing/
│   │   ├── document_ingestion.py  # Doc Intelligence + python-docx + antiword
│   │   └── chunking.py            # Fixed-size chunking with overlap
│   ├── search/
│   │   ├── search_service.py      # HR_GLOSSARY, glossary expansion, legacy search client
│   │   └── integrated_vectorization_search.py  # Hybrid search (text + vector + semantic)
│   ├── models/
│   │   └── schemas.py             # Pydantic data models
│   ├── copilot_studio/
│   │   └── service.py             # Direct-to-Engine API client
│   ├── frontend/                  # React chat UI (Option B)
│   └── frontend-copilot-studio/   # React + Copilot Studio Web Chat embed (Option B)
├── scripts/                       # See Scripts Reference below
│   ├── index_knowledge_base_docintel_chunking.py        # Pattern 1, Option 1
│   ├── index_knowledge_base_integrated_vectorization.py # Pattern 1, Option 2
│   ├── create_foundry_agent.py                          # Pattern 2
│   ├── upload_to_blob.py                                # Blob upload utility
│   ├── setup.sh                                         # Project setup
│   ├── generate_architecture_diagram.py                 # Diagram generator
│   ├── index_knowledge_base.py                          # (deprecated)
│   └── index_knowledge_base_chunking.py                 # (deprecated)
├── data/knowledge_base/           # HR policy Word documents
├── docs/
│   ├── Architecture.md            # System architecture
│   ├── ArchitectureOptions.md     # Pattern 1/2 options in detail
│   ├── DataPipelineAndTesting.md  # Data pipeline, pre-processing, and testing
│   ├── CopilotStudioIntegration.md # Copilot Studio guide (Option A)
│   └── SharePointLogicAppsArchitecture.md # Production SharePoint pipeline
├── infra/
│   └── main.bicep                 # Azure infrastructure (Bicep)
└── tests/                         # pytest test suites
```

## Scripts Reference

All scripts live in `scripts/` and share configuration from `src/config/search_config.json`.

### Indexing Scripts (choose one)

These scripts populate the Azure AI Search index (`hr-policy-index`). You only need to run **one** of the two active options.

| Script | Pattern | Pipeline | When to Use |
|--------|---------|----------|-------------|
| `index_knowledge_base_docintel_chunking.py` | Pattern 1, Option 1 | Client-side: Azure DI → `fixed_size_chunking(2000, 200)` → glossary enrichment → client embedding → Push API | Dev/test, CI/CD, custom preprocessing, batch reindexing |
| `index_knowledge_base_integrated_vectorization.py` | Pattern 1, Option 2 | Server-side: Blob upload → Indexer → Document Layout Skill (structure-aware chunking) → Embedding Skill → Index projections | Production, auto-reindex on blob changes, structure-aware chunking |

**Option 1: DocIntel + Client-Side Chunking**
```bash
# Full pipeline — extract, chunk, embed, push
python scripts/index_knowledge_base_docintel_chunking.py

# Test extraction locally (no Azure Search upload)
python scripts/index_knowledge_base_docintel_chunking.py --local-only

# Use a different data directory
python scripts/index_knowledge_base_docintel_chunking.py --data-dir data/knowledge_base_lab
```

**Option 2: Integrated Vectorization**
```bash
# Full setup — upload to blob + create index + skillset + indexer
python scripts/index_knowledge_base_integrated_vectorization.py

# Upload documents only (pipeline already exists)
python scripts/index_knowledge_base_integrated_vectorization.py --upload-only

# Create search pipeline only (documents already uploaded)
python scripts/index_knowledge_base_integrated_vectorization.py --create-pipeline-only
```

### Foundry Agent Script (Pattern 2)

Wraps the search index in a Foundry Knowledge Base and creates an agent with agentic retrieval. **Requires the index to be populated first** via one of the Pattern 1 options above.

| Script | What It Does |
|--------|--------------|
| `create_foundry_agent.py` | Creates Knowledge Source → Knowledge Base → MCP connection → Foundry Agent (`HRPolicyAgent`, gpt-4o) with `knowledge_base_retrieve` tool |

```bash
# Full setup
python scripts/create_foundry_agent.py

# Verify all Foundry IQ resources exist
python scripts/create_foundry_agent.py --verify-only

# Cleanup Foundry IQ resources
python scripts/create_foundry_agent.py --cleanup
```

### Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `upload_to_blob.py` | Upload documents to Azure Blob Storage (prerequisite for Option 2) | `python scripts/upload_to_blob.py [--dry-run] [--container NAME]` |
| `setup.sh` | One-time project setup: venv, dependencies, `.env`, frontend | `./scripts/setup.sh` |
| `generate_architecture_diagram.py` | Generate SharePoint pipeline diagram (PNG) | `python scripts/generate_architecture_diagram.py` |

### Deprecated Scripts

These are superseded and should not be used for new work:

| Script | Replaced By | Why |
|--------|-------------|-----|
| `index_knowledge_base.py` | `index_knowledge_base_docintel_chunking.py` | No chunking, no synonym map, no semantic config |
| `index_knowledge_base_chunking.py` | `index_knowledge_base_docintel_chunking.py` | Smaller chunks (500/50 vs 2000/200), no synonym map |

### Decision Flowchart

```
Need to populate the search index?
├── Yes → Do documents change frequently?
│   ├── Yes → Option 2: index_knowledge_base_integrated_vectorization.py
│   │         (auto-reindex via indexer change tracking)
│   └── No  → Option 1: index_knowledge_base_docintel_chunking.py
│             (full control, runs locally or in CI/CD)
│
Need agentic retrieval / Foundry Agent Action?
├── Yes → Run create_foundry_agent.py (after populating the index above)
└── No  → Connect Copilot Studio directly to the index as a Knowledge Source
```

> **Full details:** [docs/DataPipelineAndTesting.md](docs/DataPipelineAndTesting.md) covers the pre-processing pipeline stages, shared configuration, and testing strategy. [docs/ArchitectureOptions.md](docs/ArchitectureOptions.md) covers the architecture patterns.

---

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Only tests that don't need Azure credentials
uv run pytest tests/ -v -m mock

# Specific test file
uv run pytest tests/test_chunking.py -v
```

Test suites:
- `test_document_processing.py` — Policy number extraction, categorization, document ID generation
- `test_chunking.py` — Fixed-size chunking edge cases, deterministic IDs
- `test_search.py` — HR glossary expansion, case sensitivity, glossary integrity
- `test_backend.py` — FastAPI endpoint responses (health, glossary, chat, knowledge base)

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