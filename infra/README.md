# Infrastructure — HR Policy Knowledge Agent

This directory contains Infrastructure as Code (IaC) for deploying the Azure demo environment. Two equivalent options are provided:

| Option | Directory | Tool |
|--------|-----------|------|
| **Bicep** (recommended with `azd`) | [`bicep/`](bicep/) | Azure CLI / Azure Developer CLI |
| **Terraform** | [`terraform/`](terraform/) | Terraform CLI |

Both deploy the same set of resources into a single resource group.

## Resources Deployed

| # | Service | Purpose |
|---|---------|---------|
| 1 | **Microsoft Foundry** (AIServices) account | Unified cognitive services account (S0), system-assigned identity; parent for the project and model deployments |
| 2 | **AI Foundry Project** | Foundry project hosting Pattern A/B agents; system-assigned identity |
| 3 | **GPT-5-mini** deployment | Chat / inference (GlobalStandard, capacity 100) |
| 4 | **GPT-5** deployment | Advanced reasoning (GlobalStandard, capacity 100) |
| 5 | **text-embedding-3-small** deployment | Vector embeddings for hybrid search (GlobalStandard, capacity 120) |
| 6 | **Azure AI Search** | Hybrid search index with semantic ranker (`free` semantic tier), system-assigned identity |
| 7 | **Azure Document Intelligence** (FormRecognizer) | Document parsing / layout extraction (S0) |
| 8 | **Azure Storage Account** | Blob storage (StorageV2, Standard_LRS) with the `ask-hr-knowledge` container for uploaded documents |
| 9 | **Log Analytics workspace** | Central logs/metrics store (PerGB2018, 30-day retention) |
| 10 | **Application Insights** | Distributed tracing / APM for the backend and hosted agent (workspace-linked) |
| 11 | **Azure Managed Grafana** | Benchmark dashboards (Standard), system-assigned identity |
| 12 | **Azure Load Testing** | Non-production load testing for the benchmark (AVM module, system-assigned identity) |
| 13 | **Search diagnostic settings** | Streams Search `OperationLogs` to Log Analytics |
| 14 | **Benchmark observability** (module) | Action Group, two scheduled-query-rule alerts (failures + p95 latency), and the HR Policy Benchmark workbook |
| 15 | **Azure Container Registry** | Hosts the backend + hosted-agent images (Standard, admin user disabled) |
| 16 | **Container Apps managed environment** | Runtime environment for the backend Container App (wired to Log Analytics) |
| 17 | **User-assigned managed identity** (AcrPull) | Stable AcrPull identity so the first backend revision can always pull its image |
| 18 | **Backend Container App** | FastAPI backend (Pattern C / B2 host); system + user-assigned identity, tagged `azd-service-name: backend` |
| 19 | **Backend auth config** (optional) | Container Apps built-in Entra auth on the backend, enabled only when `backendAuthClientId` is supplied |

> The Foundry Hosted Agent is provisioned by the `azd` `postprovision` hook (a data-plane operation), not by Bicep. When its principal ID is passed back in (`hostedAgentPrincipalId`), Bicep grants that agent identity its RBAC via the `hosted-agent-rbac` module (see below).

## Entry Points

### Bicep (`azd up`)

The subscription-level entry point is [main.bicep](main.bicep), which creates the resource group and delegates to [bicep/main.bicep](bicep/main.bicep). Parameters are supplied via [main.parameters.json](main.parameters.json).

```bash
azd up
```

### Search knowledge base

Bicep provisions the Azure AI Search service and exports the shared knowledge
base contract as azd environment values. Search knowledge sources and knowledge
bases are data-plane resources, so they cannot be declared as ARM/Bicep child
resources. The `postprovision` hook in [`../azure.yaml`](../azure.yaml) upserts:

- Knowledge source: `hr-knowledge-source`
- Knowledge base: `hr-knowledge-base`
- Query-planning model: `gpt-5-mini`
- Retrieval reasoning effort: `medium`
- Output mode: `extractiveData`

The hook intentionally provisions only the shared Search resources; it does not
create a Foundry PromptAgent. It requires `hr-policy-index` to exist. For a new
environment, run the indexing pipeline and then rerun provisioning:

```bash
uv run python scripts/index_knowledge_base_integrated_vectorization.py
azd provision
```

The hook uses the preview `azure-search-documents` SDK pinned by this project
and fails provisioning if Azure rejects the knowledge-base update.

### Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in values
terraform init
terraform plan
terraform apply
```

## RBAC Roles Assigned

Roles are granted to the deploying user, service managed identities, and (optionally) the hosted agent. User grants are applied only when `principalId` / `principal_id` is supplied.

### Deploying user (`principalId`, when supplied)

| Role | Scope | Why |
|------|-------|-----|
| Azure AI User (Foundry User) | Resource group | Access the AI Foundry project |
| Cognitive Services OpenAI User | Resource group | Invoke OpenAI model deployments |
| Cognitive Services User | Resource group | Call Document Intelligence directly for client-side (Option 1) indexing |
| Search Index Data Contributor | Resource group | Read/write search index data |
| Search Service Contributor | Resource group | Manage search service configuration |
| Storage Blob Data Contributor | Resource group | Read/write blob data |
| Foundry Project Manager | Resource group | Deploy the hosted agent (create/update agent versions + agent-identity role assignments) |
| AcrPush | Container Registry | Build/push images (azd remote build / manual push) |
| Grafana Admin | Managed Grafana | Administer benchmark dashboards |

### Foundry Project managed identity

| Role | Scope | Why |
|------|-------|-----|
| Search Index Data Reader | Azure AI Search | Query the index for Pattern B (prompt agent + MCP) and Pattern A2 (Foundry IQ) |
| AcrPull | Container Registry | Platform pulls the hosted-agent image |

### Backend Container App managed identity (system-assigned)

| Role | Scope | Why |
|------|-------|-----|
| Search Index Data Reader | Azure AI Search | Query the index |
| Cognitive Services OpenAI User | AI Services account | Invoke OpenAI models |
| Azure AI User (Foundry User) | AI Services account | Access the Foundry project / agents |

### AcrPull user-assigned managed identity

| Role | Scope | Why |
|------|-------|-----|
| AcrPull | Container Registry | Pull the backend image from a stable, never-orphaned identity |

### Azure AI Search managed identity (integrated vectorization pipeline)

| Role | Scope | Why |
|------|-------|-----|
| Cognitive Services OpenAI User | AI Services account | Embedding skill (index time) + vectorizer (query time) |
| Cognitive Services User | AI Services account | Document Intelligence layout skill |
| Storage Blob Data Reader | Storage account | Indexer reads source blobs |

### Azure Managed Grafana managed identity

| Role | Scope | Why |
|------|-------|-----|
| Monitoring Reader | Log Analytics workspace | Read metrics/logs to render dashboards |

### Foundry Hosted Agent managed identity (`hosted-agent-rbac` module, when `hostedAgentPrincipalId` supplied)

| Role | Scope | Why |
|------|-------|-----|
| Search Index Data Reader | Azure AI Search | Hosted agent queries the index |
| Monitoring Metrics Publisher | Application Insights | Hosted agent publishes telemetry |

## Copilot Studio & Power Platform (not IaC-managed)

The Copilot Studio front-door agents (Patterns A, A2, B, C, and the Hosted front
door) live in **Microsoft Power Platform / Copilot Studio**, a separate SaaS
control plane. They are **not** created or governed by this Bicep/Terraform —
they are authored in the maker portal and consume the Azure resources above
(Azure AI Search, Foundry IQ, the Foundry external agent, and the backend REST
tool). This section documents what has to exist on the Power Platform side and
how it is billed, so the benchmark is reproducible end to end.

### Components (maker portal)

| Component | Purpose |
|-----------|---------|
| **Power Platform environment** | Hosts the published Copilot Studio agents; identified by `COPILOT_STUDIO_ENVIRONMENT_ID` |
| **Copilot Studio agents** | One published agent per pattern (`Ask HR Policy Agent A / A2G / B / B foundry / C`) so each end-to-end run exposes exactly one retrieval path |
| **Agent knowledge / tools** | A → Azure AI Search knowledge; A2 → Foundry IQ Knowledge Retrieval tool; B/Hosted → connected Foundry external agent; C → Azure AI Search + REST lookup tool (backend Container App) |
| **Direct Line channel** | Per-agent schema + token endpoint used by the repository benchmark to send/receive messages (`COPILOT_STUDIO_AGENT_SCHEMA*`, `COPILOT_STUDIO_TOKEN_ENDPOINT*`) |

### Identity, roles, and consent

| Grant | To | Why |
|-------|----|-----|
| Entra **app registration** (`POWER_PLATFORM_EVALUATION_CLIENT_ID`) with delegated **Power Platform API** permission (`8578e004-a5c6-46e7-913e-12f58912df43`) + tenant admin consent, native-client redirect URI | The maker running evaluations | Call `api.powerplatform.com/.../makerevaluation` for native Copilot Studio evaluations; token tenant/principal are pinned against `EXPECTED_AZURE_*` |
| **Copilot Studio maker** (author/publish) on the environment | The maker account | Create, configure, publish, and evaluate the agents |
| **Power Platform admin** (or delegated **billing/licensing reader**) | Whoever reads consumption | Read Credit consumption in the admin center for the cost lane |
| **Environment Maker / connection owner** for the Foundry connection reference | The maker account | Authorize the B/Hosted agents' connection to the Foundry external agent (a broken connection here is why those front doors return empty) |

### Cost / consumption (Credits, not Azure USD)

Copilot Studio bills in **Copilot Credits**, rated per agent activity and tracked separately from
Azure per-token USD:

- **Estimate:** `python -m src.benchmarking.copilot_credits_cli estimate --pattern <A|A2|B|C|Hosted>` using the rate card at [`../experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json`](../experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json).
- **Billed (authoritative):** Power Platform admin center → **Licensing → Copilot Studio → Environments** (Copilot credit consumption grid). Export the grid and reconcile with `copilot_credits_cli reconcile`.
- **Bring-your-own-model note:** for Pattern B and the Hosted front door, the connected **Foundry** model's tokens are billed on the Azure per-token USD lane **in addition** to the Copilot Credits — never merge the two.

## Prerequisites

- Azure subscription with access to Azure OpenAI (GPT-5-mini) and AI Search
- Azure CLI (`az`) logged in, or Terraform CLI with `azurerm` provider configured
- For Bicep: Azure Developer CLI (`azd`) recommended
- For Terraform: version >= 1.5.0
