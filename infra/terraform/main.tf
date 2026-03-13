# ============================================================================
# HR Policy Knowledge Agent - Demo Infrastructure (Terraform)
# Main Resources — mirrors infra/bicep/main.bicep
#
# Demo-only services:
#   1. Resource Group
#   2. Azure AI Foundry (AIServices) + Project
#   3. GPT-4o deployment
#   4. text-embedding-3-small deployment
#   5. Azure AI Search (semantic ranker)
#   6. Azure Document Intelligence
#   7. Azure Storage Account + blob container
#   8. RBAC role assignments
# ============================================================================

locals {
  resource_token = "${var.resource_prefix}-${random_string.suffix.result}"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# ============================================================================
# 1. Resource Group
# ============================================================================
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.resource_prefix}-${var.environment_name}"
  location = var.location
}

# ============================================================================
# 2. Azure AI Foundry (AIServices) — unified cognitive services account
# ============================================================================
resource "azurerm_ai_services" "ai_services" {
  name                  = "cog-${local.resource_token}"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  sku_name              = "S0"
  custom_subdomain_name = "cog-${local.resource_token}"
  public_network_access = "Enabled"
  local_authentication_enabled = true

  identity {
    type = "SystemAssigned"
  }
}

# ============================================================================
# 3. GPT-4o Deployment (chat / inference)
# ============================================================================
resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = var.openai_deployment_name
  cognitive_account_id = azurerm_ai_services.ai_services.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 100
  }
}

# ============================================================================
# 4. text-embedding-3-small Deployment (vector embeddings)
# ============================================================================
resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_deployment_name
  cognitive_account_id = azurerm_ai_services.ai_services.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = 120
  }

  depends_on = [azurerm_cognitive_deployment.gpt4o]
}

# ============================================================================
# 5. Azure AI Search (semantic ranker enabled)
# ============================================================================
resource "azurerm_search_service" "search" {
  name                = "srch-${local.resource_token}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = var.search_sku
  replica_count       = 1
  partition_count     = 1
  semantic_search_sku = "free"
}

# ============================================================================
# 6. Azure Document Intelligence (FormRecognizer)
# ============================================================================
resource "azurerm_cognitive_account" "doc_intelligence" {
  name                  = "frm-${local.resource_token}"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "frm-${local.resource_token}"
  public_network_access_enabled = true
}

# ============================================================================
# 7. Azure Storage Account + blob container
# ============================================================================
resource "azurerm_storage_account" "storage" {
  name                     = "st${random_string.suffix.result}"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_id    = azurerm_storage_account.storage.id
  container_access_type = "private"
}

# ============================================================================
# 8. RBAC Role Assignments (for demo user principal)
# ============================================================================

# Azure AI User
resource "azurerm_role_assignment" "ai_user" {
  count                = var.principal_id != "" ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Azure AI User"
  principal_id         = var.principal_id
}

# Cognitive Services OpenAI User
resource "azurerm_role_assignment" "openai_user" {
  count                = var.principal_id != "" ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.principal_id
}

# Search Index Data Contributor
resource "azurerm_role_assignment" "search_data_contributor" {
  count                = var.principal_id != "" ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = var.principal_id
}

# Search Service Contributor
resource "azurerm_role_assignment" "search_service_contributor" {
  count                = var.principal_id != "" ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Search Service Contributor"
  principal_id         = var.principal_id
}

# Storage Blob Data Contributor
resource "azurerm_role_assignment" "storage_blob_contributor" {
  count                = var.principal_id != "" ? 1 : 0
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.principal_id
}
