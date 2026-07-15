// ============================================================================
// HR Policy Knowledge Agent - Demo Resources (Resource Group scope)
// Deploys ONLY the services needed for a demo:
//   1. Azure AI Foundry (AIServices) + Project
//   2. GPT-4.1 deployment (chat/inference)
//   3. GPT-5 deployment (advanced reasoning)
//   4. text-embedding-3-small deployment (vector embeddings)
//   5. Azure AI Search (semantic ranker enabled)
//   6. Azure Document Intelligence
//   7. Azure Storage Account
//   8. RBAC role assignments
// ============================================================================

@description('Name of the azd environment')
param environmentName string

@description('Azure region for all resources')
param location string

@description('Resource prefix for naming')
param resourcePrefix string

@description('Azure OpenAI chat model deployment name')
param openAIDeploymentName string

@description('Azure OpenAI GPT-5 deployment name')
param gpt5DeploymentName string

@description('Azure OpenAI embedding model deployment name')
param embeddingDeploymentName string

@description('Azure AI Search SKU')
param searchSku string

@description('Principal ID for RBAC role assignments')
param principalId string

@description('Optional Entra app registration (client) ID used to protect the backend Container App with Microsoft Entra authentication (Container Apps built-in auth). Leave empty for public ingress (demo).')
param backendAuthClientId string = ''

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
// 3. GPT-4.1 Deployment (chat / inference)
// ============================================================================
resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: openAIDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
  }
}

// ============================================================================
// 4. GPT-5 Deployment (advanced reasoning)
// ============================================================================
resource gpt5Deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: gpt5DeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5'
      version: '2025-08-07'
    }
  }
  dependsOn: [gpt41Deployment]
}

// ============================================================================
// 5. text-embedding-3-small Deployment (vector embeddings for hybrid search)
// ============================================================================
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiServices
  name: embeddingDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 120
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
  dependsOn: [gpt5Deployment]
}

// ============================================================================
// 6. Azure AI Search (semantic ranker enabled for hybrid search)
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
// 7. Azure Document Intelligence (FormRecognizer)
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
// 8. Azure Storage Account (document uploads + blob storage)
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
  name: 'ask-hr-knowledge'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// 9. Observability — Log Analytics + Application Insights
//    (App Insights connection string is injected into the backend + hosted agent)
// ============================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
  location: location
  properties: {
    retentionInDays: 30
    sku: { name: 'PerGB2018' }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${abbrs.insightsComponents}${resourceToken}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ============================================================================
// 10. Azure Container Registry — hosts the backend + hosted-agent images
// ============================================================================
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${abbrs.containerRegistryRegistries}${replace(resourceToken, '-', '')}'
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
  }
}

// ============================================================================
// 11. Container Apps — environment + FastAPI backend (Pattern C / B2 host)
//     azd builds and pushes the image, then updates this app (azd-service-name).
// ============================================================================
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${abbrs.appManagedEnvironments}${resourceToken}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${abbrs.appContainerApps}backend-${uniqueSuffix}'
  location: location
  identity: { type: 'SystemAssigned' }
  tags: { 'azd-service-name': 'backend' }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          // Placeholder image; azd replaces it with the built backend image.
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'AZURE_SEARCH_INDEX_NAME', value: 'hr-policy-index' }
            { name: 'AZURE_AI_PROJECT_ENDPOINT', value: '${aiServices.properties.endpoint}/api/projects/${aiProject.name}' }
            { name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME', value: openAIDeploymentName }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'ENABLE_TRACING', value: 'true' }
            { name: 'PORT', value: '8000' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

// Optional: protect the backend with Microsoft Entra authentication (Container
// Apps built-in auth / "Easy Auth"). Enabled only when backendAuthClientId is
// supplied (an Entra app registration created by an admin — standard users in
// locked-down tenants can't self-create one). When empty, the backend uses
// public ingress, which is fine for a demo; once enabled, use OAuth 2.0 in
// Copilot Studio's REST tool. Token-validation only (callers present their own
// bearer tokens), so no client secret is required.
resource backendAuth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = if (!empty(backendAuthClientId)) {
  parent: backendApp
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'Return401'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: backendAuthClientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
        }
        validation: {
          allowedAudiences: [
            'api://${backendAuthClientId}'
          ]
        }
      }
    }
  }
}

// ============================================================================
// 12. RBAC Role Assignments (for demo user principal)
// ============================================================================

// Azure AI User — access to AI Foundry project
// Renamed to "Foundry User" in the Foundry RBAC rename (role ID unchanged).
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

// Search Index Data Reader — lets the Foundry PROJECT managed identity query the
// index. Required for Pattern B (prompt agent + MCP), Pattern A2 (Foundry IQ),
// and the Hosted Agent — the Foundry side reads Search under the project identity.
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
resource projectSearchReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, aiProject.id, searchIndexDataReaderRoleId)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Foundry Project Manager — required for the demo USER to DEPLOY a hosted agent
// (create/update agent versions and the platform-created agent identity's role
// assignments). Previously named "Azure AI Project Manager" (role ID unchanged).
var foundryProjectManagerRoleId = 'eadc314b-1a2d-4efa-be10-5d325db5065e'
resource userFoundryProjectManagerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(resourceGroup().id, principalId, foundryProjectManagerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryProjectManagerRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// ---- Container Registry + Container Apps identities ----
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'

// AcrPull for the backend Container App MI (pull its own image from ACR).
resource backendAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, backendApp.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// AcrPull for the Foundry PROJECT MI — the platform pulls the hosted-agent image.
resource projectAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, aiProject.id, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// AcrPush for the demo USER — build/push images (azd remote build / manual push).
resource userAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(containerRegistry.id, principalId, acrPushRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPushRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

// Backend Container App MI → Search Index Data Reader (query the index).
resource backendSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, backendApp.id, searchIndexDataReaderRoleId)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Backend Container App MI → Cognitive Services OpenAI User (invoke models).
resource backendOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, backendApp.id, cognitiveServicesOpenAIUserRoleId)
  scope: aiServices
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Backend Container App MI → Foundry User (access the Foundry project/agents).
resource backendAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, backendApp.id, azureAIUserRoleId)
  scope: aiServices
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Outputs
// ============================================================================
output openAIEndpoint string = aiServices.properties.endpoint
output openAIDeploymentName string = openAIDeploymentName
output gpt5DeploymentName string = gpt5DeploymentName
output embeddingDeploymentName string = embeddingDeploymentName
output aiFoundryResourceName string = aiServices.name
output aiProjectName string = aiProject.name
output projectEndpoint string = '${aiServices.properties.endpoint}/api/projects/${aiProject.name}'
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchName string = search.name
output docIntelligenceEndpoint string = docIntelligence.properties.endpoint
output storageAccountName string = storage.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output containerRegistryName string = containerRegistry.name
output containerAppsEnvironmentName string = containerAppsEnv.name
output backendAppName string = backendApp.name
output backendAppUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output applicationInsightsName string = appInsights.name
