# Terraform — HR Policy Knowledge Agent

Terraform configuration that mirrors the Bicep deployment, deploying all demo resources into a single resource group.

## File Structure

| File | Description |
|------|-------------|
| [providers.tf](providers.tf) | Provider config (`azurerm ~> 4.0`, `random ~> 3.6`); requires Terraform >= 1.5.0 |
| [variables.tf](variables.tf) | Input variable definitions with defaults and validation |
| [main.tf](main.tf) | All resource definitions and RBAC role assignments |
| [outputs.tf](outputs.tf) | Output values (endpoints, names) |
| [terraform.tfvars.example](terraform.tfvars.example) | Example variable values — copy to `terraform.tfvars` |

## Quick Start

```bash
cd infra/terraform

# 1. Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set subscription_id and principal_id at minimum

# 2. Deploy
terraform init
terraform plan
terraform apply
```

To get your principal ID:

```bash
az ad signed-in-user show --query id -o tsv
```

## Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `subscription_id` | string | _(required)_ | Azure subscription ID |
| `environment_name` | string | _(required)_ | Environment name (e.g. `demo`) |
| `location` | string | `eastus2` | Azure region |
| `resource_prefix` | string | `hr-policy-kb` | Prefix for resource naming |
| `openai_deployment_name` | string | `gpt-4o` | GPT-4o deployment name |
| `embedding_deployment_name` | string | `text-embedding-3-small` | Embedding model deployment name |
| `search_sku` | string | `basic` | AI Search SKU (`basic` or `standard`) |
| `principal_id` | string | `""` | User/SP object ID for RBAC; leave empty to skip |

## Outputs

| Output | Description |
|--------|-------------|
| `resource_group_name` | Resource group name |
| `openai_endpoint` | AI Foundry / OpenAI endpoint URL |
| `openai_deployment_name` | GPT-4o deployment name |
| `embedding_deployment_name` | Embedding deployment name |
| `ai_foundry_resource_name` | AI Foundry account name |
| `search_endpoint` | AI Search endpoint URL |
| `search_name` | AI Search service name |
| `doc_intelligence_endpoint` | Document Intelligence endpoint URL |
| `storage_account_name` | Storage account name |

## Tear Down

```bash
terraform destroy
```

> **Note**: The provider is configured with `purge_soft_delete_on_destroy = true` for Cognitive Services accounts, so destroyed resources won't linger in soft-delete state.
