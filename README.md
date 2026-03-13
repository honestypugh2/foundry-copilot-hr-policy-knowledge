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

```
 React UI / Copilot Studio
          │
          ▼
    FastAPI Backend
          │
  ┌───────┼───────┐
  ▼       ▼       ▼
Query   Policy   Answer
Understand Retrieval Generation
(Glossary) (AI Search) (RAG + LLM)
```

See [docs/Architecture.md](docs/Architecture.md) for the full diagram.

## Tech Stack

- **Azure AI Foundry** — `azure-ai-projects>=2.0.0`
- **Microsoft Agent Framework** — `agent-framework --pre` (Sequential Workflows)
- **Azure AI Search** — Full-text + semantic search with HR glossary
- **Azure Document Intelligence** — Word document extraction
- **Azure OpenAI** — GPT-4o for answer generation
- **Copilot Studio** — Teams / web chat interface
- **FastAPI** — REST API backend
- **React + TypeScript + Vite** — Chat UI

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — Python package installer and runner
- Node.js 18+ (for frontend)
- Azure subscription with AI Search, OpenAI, and Document Intelligence
- Azure CLI (`az login`)

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

### 4. Start the Backend

```bash
uv run python -m src.backend.main
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 5. Start the Frontend

**Primary frontend (AI Agent Framework):**
```bash
cd src/frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

**Copilot Studio frontend:**
```bash
cd src/frontend-copilot-studio
npm install
npm run dev
# UI available at http://localhost:5174
```

## API Endpoints

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

## Project Structure

```
├── src/
│   ├── agents/
│   │   ├── hr_policy_agent.py     # RAG agent with grounding rules
│   │   └── orchestrator.py        # Sequential workflow (WorkflowBuilder)
│   ├── backend/
│   │   └── main.py                # FastAPI application
│   ├── document_processing/
│   │   └── document_ingestion.py  # Doc Intelligence + python-docx
│   ├── search/
│   │   └── search_service.py      # AI Search + HR glossary
│   ├── models/
│   │   └── schemas.py             # Pydantic data models
│   ├── copilot_studio/
│   │   └── service.py             # Direct-to-Engine API client
│   ├── frontend/                  # React + TypeScript + Vite (Agent Framework)
│   └── frontend-copilot-studio/   # React + Copilot Studio Web Chat embed
├── scripts/
│   ├── index_knowledge_base.py    # Batch indexing script
│   └── setup.sh                   # Project setup
├── data/knowledge_base/           # HR policy Word documents
├── docs/
│   ├── Architecture.md            # System architecture
│   └── CopilotStudioIntegration.md # Copilot Studio guide
├── infra/
│   └── main.bicep                 # Azure infrastructure
└── tests/
```

## Copilot Studio Integration

See [docs/CopilotStudioIntegration.md](docs/CopilotStudioIntegration.md) for step-by-step instructions on connecting this agent to Copilot Studio for Teams deployment.

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