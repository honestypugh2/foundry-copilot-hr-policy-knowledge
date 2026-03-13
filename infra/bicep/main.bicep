// ============================================================================
// HR Policy Knowledge Agent - Demo Resources (Resource Group scope)
// Deploys ONLY the services needed for a demo:
//   1. Azure AI Foundry (AIServices) + Project
//   2. GPT-4o deployment (chat/inference)
//   3. text-embedding-3-small deployment (vector embeddings)
//   4. Azure AI Search (semantic ranker enabled)
//   5. Azure Document Intelligence
//   6. Azure Storage Account
//   7. RBAC role assignments
// ============================================================================

@description('Name of the azd environment')
param environmentName string

@description('Azure region for all resources')
param location string

@description('Resource prefix for naming')
param resourcePrefix string

@description('Azure OpenAI chat model deployment name')
param openAIDeploymentName string

@description('Azure OpenAI embedding model deployment name')
param embeddingDeploymentName string

@description('Azure AI Search SKU')
param searchSku string

@description('Principal ID for RBAC role assignments')
param principalId string

// ---------- Naming ----------
var abbrs = loadJsonContent('./abbreviations.json')
var uniqueSuffix = uniqueString(resourceGroup().id)
var resourceToken = toLower('${resourcePrefix}-${uniqueSuffix}')

// ============================================================================
// 1. Azure AI Foundry (AIServices) — unified cognitive services account
// ============================================================================
resource aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: '${abbrs.cognitiveServicesAccounts}${resourceToken}'
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
    disableLocalAuth: false
  }
}

// ============================================================================
// 2. AI Foundry Project (child of AIServices)
// ============================================================================
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiServices
  name: '${abbrs.cognitiveServicesProjects}${resourceToken}'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'HR Policy Knowledge Agent - Demo Project'
  }
}

// ============================================================================
// 3. GPT-4o Deployment (chat / inference)
// ============================================================================
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: openAIDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
  }
}

// ============================================================================
// 3. text-embedding-3-small Deployment (vector embeddings for hybrid search)
// ============================================================================
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: 120
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
  dependsOn: [gpt4oDeployment]
}

// ============================================================================
// 4. Azure AI Search (semantic ranker enabled for hybrid search)
// ============================================================================
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: '${abbrs.searchSearchServices}${resourceToken}'
  location: location
  sku: { name: searchSku }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'free'
  }
}

// ============================================================================
// 5. Azure Document Intelligence (FormRecognizer)
// ============================================================================
resource docIntelligence 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
  location: location
  kind: 'FormRecognizer'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// 6. Azure Storage Account (document uploads + blob storage)
// ============================================================================
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${abbrs.storageStorageAccounts}${uniqueSuffix}'
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// 7. RBAC Role Assignments (for demo user principal)
// ============================================================================

// Azure AI User — access to AI Foundry project
var azureAIUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
resource aiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, azureAIUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// Cognitive Services OpenAI User — invoke OpenAI models
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource openAIUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, cognitiveServicesOpenAIUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// Search Index Data Contributor — manage search index data
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
resource searchDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, searchIndexDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// Search Service Contributor — manage search service
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
resource searchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, searchServiceContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// Storage Blob Data Contributor — read/write blob data
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, storageBlobDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// ============================================================================
// Outputs
// ============================================================================
output openAIEndpoint string = aiServices.properties.endpoint
output openAIDeploymentName string = openAIDeploymentName
output embeddingDeploymentName string = embeddingDeploymentName
output aiFoundryResourceName string = aiServices.name
output aiProjectName string = aiProject.name
output projectEndpoint string = '${aiServices.properties.endpoint}/api/projects/${aiProject.name}'
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
output docIntelligenceEndpoint string = docIntelligence.properties.endpoint
output storageAccountName string = storage.name
