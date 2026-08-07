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
param openAIDeploymentName string = 'gpt-5-mini'

@description('Azure OpenAI GPT-5 deployment name')
param gpt5DeploymentName string = 'gpt-5'

@description('Azure OpenAI embedding model deployment name')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Search knowledge source provisioned by the postprovision data-plane hook')
param searchKnowledgeSourceName string = 'hr-knowledge-source'

@description('Search knowledge base provisioned by the postprovision data-plane hook')
param searchKnowledgeBaseName string = 'hr-knowledge-base'

@description('Model deployment used by the Search knowledge base for query planning')
param searchKnowledgeBaseModelDeployment string = 'gpt-5-mini'

@allowed(['minimal', 'low', 'medium'])
@description('Reasoning effort used by the Search knowledge base for retrieval planning')
param searchKnowledgeBaseReasoningEffort string = 'medium'

@allowed(['answerSynthesis', 'extractiveData'])
@description('Output mode returned by the Search knowledge base')
param searchKnowledgeBaseOutputMode string = 'extractiveData'

@description('Preview Search API version used by the knowledge base MCP endpoint')
param searchMcpApiVersion string = '2026-05-01-preview'

@description('Azure AI Search SKU')
@allowed(['basic', 'standard'])
param searchSku string = 'basic'

@description('Principal ID for RBAC role assignments (e.g. your user or service principal objectId)')
param principalId string = ''

@description('Optional Entra app registration (client) ID to protect the backend Container App with Microsoft Entra authentication. Leave empty for public ingress (demo).')
param backendAuthClientId string = ''

@description('Region for Azure AI Search. Defaults to the main location; override when the main region is out of Search capacity.')
param searchLocation string = ''

@description('Full backend container image reference (ACR). When empty, a placeholder image is used and azd updates it on deploy.')
param backendImage string = ''

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
    gpt5DeploymentName: gpt5DeploymentName
    embeddingDeploymentName: embeddingDeploymentName
    searchKnowledgeSourceName: searchKnowledgeSourceName
    searchKnowledgeBaseName: searchKnowledgeBaseName
    searchKnowledgeBaseModelDeployment: searchKnowledgeBaseModelDeployment
    searchKnowledgeBaseReasoningEffort: searchKnowledgeBaseReasoningEffort
    searchKnowledgeBaseOutputMode: searchKnowledgeBaseOutputMode
    searchMcpApiVersion: searchMcpApiVersion
    searchSku: searchSku
    principalId: principalId
    backendAuthClientId: backendAuthClientId
    searchLocation: searchLocation
    backendImage: backendImage
  }
}

// ---------- Outputs (surfaced to azd) ----------
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_OPENAI_ENDPOINT string = resources.outputs.openAIEndpoint
output AZURE_OPENAI_DEPLOYMENT string = resources.outputs.openAIDeploymentName
output AZURE_GPT5_DEPLOYMENT string = resources.outputs.gpt5DeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = resources.outputs.embeddingDeploymentName
output AZURE_AI_FOUNDRY_RESOURCE string = resources.outputs.aiFoundryResourceName
output AZURE_AI_PROJECT_NAME string = resources.outputs.aiProjectName
output AZURE_AI_PROJECT_ENDPOINT string = resources.outputs.projectEndpoint
output AZURE_SEARCH_ENDPOINT string = resources.outputs.searchEndpoint
output AZURE_SEARCH_NAME string = resources.outputs.searchName
output AZURE_SEARCH_INDEX_NAME string = 'hr-policy-index'
output AZURE_SEARCH_KNOWLEDGE_SOURCE_NAME string = resources.outputs.knowledgeSourceName
output AZURE_SEARCH_KNOWLEDGE_BASE_NAME string = resources.outputs.knowledgeBaseName
output AZURE_SEARCH_KB_MODEL_DEPLOYMENT string = resources.outputs.knowledgeBaseModelDeployment
output AZURE_SEARCH_KB_REASONING_EFFORT string = resources.outputs.knowledgeBaseReasoningEffort
output AZURE_SEARCH_KB_OUTPUT_MODE string = resources.outputs.knowledgeBaseOutputMode
output AZURE_SEARCH_MCP_API_VERSION string = resources.outputs.searchMcpApiVersion
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = resources.outputs.docIntelligenceEndpoint
output AZURE_STORAGE_ACCOUNT string = resources.outputs.storageAccountName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = resources.outputs.containerRegistryName
output AZURE_CONTAINER_APPS_ENVIRONMENT string = resources.outputs.containerAppsEnvironmentName
output SERVICE_BACKEND_NAME string = resources.outputs.backendAppName
output SERVICE_BACKEND_URI string = resources.outputs.backendAppUrl
output APPLICATIONINSIGHTS_CONNECTION_STRING string = resources.outputs.applicationInsightsConnectionString
output APPLICATIONINSIGHTS_NAME string = resources.outputs.applicationInsightsName
