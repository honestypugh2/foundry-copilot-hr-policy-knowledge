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
| 1 | **Azure AI Foundry** (AIServices) + Project | Unified cognitive services account |
| 2 | **GPT-4o** deployment | Chat / inference (GlobalStandard, 100 capacity) |
| 3 | **text-embedding-3-small** deployment | Vector embeddings for hybrid search (Standard, 120 capacity) |
| 4 | **Azure AI Search** | Hybrid search index with semantic ranker (`free` tier) |
| 5 | **Azure Document Intelligence** | Document parsing (prebuilt-layout, S0) |
| 6 | **Azure Storage Account** | Blob storage for uploaded documents |
| 7 | **RBAC role assignments** | Least-privilege access for the demo user |

## Entry Points

### Bicep (`azd up`)

The subscription-level entry point is [main.bicep](main.bicep), which creates the resource group and delegates to [bicep/main.bicep](bicep/main.bicep). Parameters are supplied via [main.parameters.json](main.parameters.json).

```bash
azd up
```

### Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in values
terraform init
terraform plan
terraform apply
```

## RBAC Roles Assigned

When `principalId` / `principal_id` is provided, these roles are granted at resource-group scope:

| Role | Purpose |
|------|---------|
| Azure AI User | Access AI Foundry project |
| Cognitive Services OpenAI User | Invoke OpenAI model deployments |
| Search Index Data Contributor | Read/write search index data |
| Search Service Contributor | Manage search service configuration |
| Storage Blob Data Contributor | Read/write blob data |

## Prerequisites

- Azure subscription with access to Azure OpenAI (GPT-4o) and AI Search
- Azure CLI (`az`) logged in, or Terraform CLI with `azurerm` provider configured
- For Bicep: Azure Developer CLI (`azd`) recommended
- For Terraform: version >= 1.5.0
