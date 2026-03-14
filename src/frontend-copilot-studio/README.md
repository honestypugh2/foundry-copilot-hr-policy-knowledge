# Ask HR — Copilot Studio Frontend

React frontend that embeds the Copilot Studio HR Policy agent using the Bot Framework Web Chat SDK. Provides two chat modes and informational pages for setup and architecture.

## Prerequisites

- **Node.js** 18+ and **npm**
- **FastAPI backend** running at `http://localhost:8000` (Vite proxies `/api` requests to it)
- **Copilot Studio agent** configured with Azure AI Search knowledge source
- Environment variables set in the root `.env` file (see below)

## Quick Start

```bash
# 1. Start the FastAPI backend (from the project root)
cd /path/to/foundry-copilot-hr-policy-knowledge
source .venv/bin/activate
uvicorn src.backend.main:app --reload --port 8000

# 2. In a separate terminal, start the frontend
cd src/frontend-copilot-studio
npm install
npm run dev
```

The app will be available at **http://localhost:5174**.

## Environment Variables

These must be set in the root `.env` file (the backend reads them and exposes them via API):

| Variable | Description | Required |
|---|---|---|
| `COPILOT_STUDIO_ENVIRONMENT_ID` | Power Platform environment ID | Yes |
| `COPILOT_STUDIO_AGENT_SCHEMA` | Agent schema name (e.g. `cr4ba_askHrPolicyAgent`) | Yes |
| `COPILOT_STUDIO_REGION` | Region prefix (default: `unitedstates`) | No |
| `COPILOT_STUDIO_TOKEN_ENDPOINT` | Full token endpoint URL (overrides auto-built URL) | No |

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server on port 5174 with HMR |
| `npm run build` | Type-check with `tsc` and build for production |
| `npm run preview` | Preview the production build locally |

## Chat Modes

### Web Chat Embed (default)

Uses the **Bot Framework Web Chat** widget connected via a Direct Line token fetched from the backend (`GET /api/copilot-studio/token`). Supports rich cards, adaptive cards, and all native Copilot Studio features.

### Backend Proxy

A simple chat UI that routes messages through the FastAPI backend (`POST /api/copilot-studio/chat`). Useful when:
- The Direct Line token endpoint isn't accessible
- You want server-side logging of all conversations
- You need to test the backend proxy flow

Toggle between modes using the buttons in the top-right of the Chat page.

## Pages

| Route | Page | Description |
|---|---|---|
| `/` | **Chat** | Main chat interface with mode toggle |
| `/setup` | **Setup Guide** | Step-by-step Copilot Studio configuration guide |
| `/architecture` | **Architecture** | System architecture overview |

## Testing the Chat

1. Open http://localhost:5174
2. The app checks if the backend has valid Copilot Studio configuration
3. If configured, select a chat mode and ask HR policy questions:
   - "What is the PTO policy?"
   - "How many holidays do we get?"
   - "What's the dress code?"
   - "Tell me about the probationary period"
   - "What is policy 50410?"
4. Verify that answers cite specific policy numbers and document titles

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Checking Copilot Studio configuration…" spinner never resolves | Backend not running | Start the FastAPI backend on port 8000 |
| "Not Configured" banner | Missing `COPILOT_STUDIO_ENVIRONMENT_ID` or `COPILOT_STUDIO_AGENT_SCHEMA` in `.env` | Add the required env vars and restart the backend |
| "Failed to get Direct Line token" | Token endpoint unreachable or wrong credentials | Verify `COPILOT_STUDIO_TOKEN_ENDPOINT` or check that the agent is published in Copilot Studio |
| CORS errors in browser console | Backend CORS not configured for frontend origin | The Vite proxy should handle this; ensure you're accessing via `localhost:5174`, not a different host |
| Proxy mode returns errors | Backend can't reach Copilot Studio API | Check backend logs, verify Entra ID credentials (`az login`) |

## Tech Stack

- **React 19** with TypeScript
- **Vite 6** (dev server + build)
- **Tailwind CSS 4** (styling)
- **Bot Framework Web Chat** (Direct Line embed)
- **React Router 7** (client-side routing)
- **Axios** (API calls)

## Project Structure

```
src/frontend-copilot-studio/
├── index.html              # HTML entry point
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite config (port 5174, /api proxy)
└── src/
    ├── main.tsx            # React entry point
    ├── App.tsx             # Router and navigation
    ├── index.css           # Global styles (Tailwind)
    ├── botframework-webchat.d.ts  # Type declarations for Web Chat
    ├── pages/
    │   ├── ChatPage.tsx        # Chat interface (embed + proxy modes)
    │   ├── SetupGuidePage.tsx  # Copilot Studio setup instructions
    │   └── ArchitecturePage.tsx # Architecture diagram
    └── services/
        └── api.ts          # Backend API client functions
```
