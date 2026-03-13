// ============================================================================
// HR Policy Knowledge Agent - Demo Infrastructure
// Subscription-level entry point (creates resource group + delegates to module)
// Pattern: github.com/honestypugh2/foundry-grant-eo-validation-demo
// ============================================================================
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment (used as resource prefix)')
param environmentName string

@description('Azure region for all resources')
param location string

@description('Resource prefix for naming')
param resourcePrefix string = 'hr-policy-kb'

@description('Azure OpenAI chat model deployment name')
param openAIDeploymentName string = 'gpt-4o'

@description('Azure OpenAI embedding model deployment name')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Azure AI Search SKU')
@allowed(['basic', 'standard'])
param searchSku string = 'basic'

@description('Principal ID for RBAC role assignments (e.g. your user or service principal objectId)')
param principalId string = ''

// ---------- Resource Group ----------
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${resourcePrefix}-${environmentName}'
  location: location
}

// ---------- Deploy all demo resources into the resource group ----------
module resources './bicep/main.bicep' = {
  name: 'resources-${environmentName}'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    resourcePrefix: resourcePrefix
    openAIDeploymentName: openAIDeploymentName
    embeddingDeploymentName: embeddingDeploymentName
    searchSku: searchSku
    principalId: principalId
  }
}

// ---------- Outputs (surfaced to azd) ----------
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_OPENAI_ENDPOINT string = resources.outputs.openAIEndpoint
output AZURE_OPENAI_DEPLOYMENT string = resources.outputs.openAIDeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = resources.outputs.embeddingDeploymentName
output AZURE_AI_FOUNDRY_RESOURCE string = resources.outputs.aiFoundryResourceName
output AZURE_AI_PROJECT_NAME string = resources.outputs.aiProjectName
output AZURE_AI_PROJECT_ENDPOINT string = resources.outputs.projectEndpoint
output AZURE_SEARCH_ENDPOINT string = resources.outputs.searchEndpoint
output AZURE_SEARCH_NAME string = resources.outputs.searchName
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = resources.outputs.docIntelligenceEndpoint
output AZURE_STORAGE_ACCOUNT string = resources.outputs.storageAccountName
