# Bicep — HR Policy Knowledge Agent

Resource-group-scoped Bicep module that deploys all demo resources.

## File Structure

| File | Description |
|------|-------------|
| [main.bicep](main.bicep) | All resource definitions, RBAC assignments, and outputs |
| [abbreviations.json](abbreviations.json) | Resource naming prefixes (e.g. `cog-`, `srch-`, `st`) |

The parent entry point is [`../main.bicep`](../main.bicep) (subscription scope), which creates the resource group and invokes this module.

## Deploying with `azd`

```bash
# From the repo root
azd auth login
azd up
```

`azd` reads [`../main.parameters.json`](../main.parameters.json) and populates values from environment variables (`AZURE_ENV_NAME`, `AZURE_LOCATION`, `AZURE_PRINCIPAL_ID`).

## Deploying with Azure CLI

```bash
az deployment sub create \
  --location eastus2 \
  --template-file ../main.bicep \
  --parameters ../main.parameters.json \
  --parameters environmentName=demo location=eastus2 principalId=$(az ad signed-in-user show --query id -o tsv)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `environmentName` | string | _(required)_ | Environment name used as suffix in resource group and resource names |
| `location` | string | _(required)_ | Azure region for all resources |
| `resourcePrefix` | string | `hr-policy-kb` | Prefix for resource naming |
| `openAIDeploymentName` | string | `gpt-4o` | GPT-4o deployment name |
| `embeddingDeploymentName` | string | `text-embedding-3-small` | Embedding model deployment name |
| `searchSku` | string | `basic` | AI Search SKU (`basic` or `standard`) |
| `principalId` | string | `""` | User/SP object ID for RBAC; leave empty to skip role assignments |

## Outputs

| Output | Description |
|--------|-------------|
| `openAIEndpoint` | AI Foundry / OpenAI endpoint URL |
| `openAIDeploymentName` | GPT-4o deployment name |
| `embeddingDeploymentName` | Embedding deployment name |
| `aiFoundryResourceName` | AI Foundry account resource name |
| `aiProjectName` | AI Foundry project name |
| `projectEndpoint` | Full project endpoint URL |
| `searchEndpoint` | AI Search endpoint URL |
| `searchName` | AI Search service name |
| `docIntelligenceEndpoint` | Document Intelligence endpoint URL |
| `storageAccountName` | Storage account name |

## Naming Convention

Resources are named using the pattern: `{abbreviation}{resourcePrefix}-{uniqueSuffix}`

Abbreviations come from [abbreviations.json](abbreviations.json), following the [Azure naming convention guidance](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations).
