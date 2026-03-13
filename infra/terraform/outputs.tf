# ============================================================================
# HR Policy Knowledge Agent - Demo Infrastructure (Terraform)
# Outputs
# ============================================================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "openai_endpoint" {
  description = "Azure OpenAI / AI Foundry endpoint"
  value       = azurerm_ai_services.ai_services.endpoint
}

output "openai_deployment_name" {
  description = "GPT-4o deployment name"
  value       = azurerm_cognitive_deployment.gpt4o.name
}

output "embedding_deployment_name" {
  description = "Embedding model deployment name"
  value       = azurerm_cognitive_deployment.embedding.name
}

output "ai_foundry_resource_name" {
  description = "AI Foundry (AIServices) resource name"
  value       = azurerm_ai_services.ai_services.name
}

output "search_endpoint" {
  description = "Azure AI Search endpoint"
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "search_name" {
  description = "Azure AI Search service name"
  value       = azurerm_search_service.search.name
}

output "doc_intelligence_endpoint" {
  description = "Azure Document Intelligence endpoint"
  value       = azurerm_cognitive_account.doc_intelligence.endpoint
}

output "storage_account_name" {
  description = "Azure Storage Account name"
  value       = azurerm_storage_account.storage.name
}
