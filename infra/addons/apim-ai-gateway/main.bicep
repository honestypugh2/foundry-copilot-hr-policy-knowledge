// Stand-alone add-on: APIM AI gateway in front of the existing Foundry / Azure OpenAI account.
// Deploy with `az deployment group create` into the existing resource group (not part of azd).
targetScope = 'resourceGroup'

@description('Region for APIM. Defaults to the resource group region.')
param location string = resourceGroup().location

@description('Short unique suffix for the APIM name.')
param suffix string = take(uniqueString(resourceGroup().id), 6)

@description('Existing Foundry / Azure OpenAI (AIServices) account name.')
param aiAccountName string

@description('Existing Application Insights component name.')
param appInsightsName string

@description('Existing Log Analytics workspace name.')
param logAnalyticsName string

@description('APIM publisher email.')
param publisherEmail string

@description('APIM publisher name.')
param publisherName string = 'pwwdemo'

var tags = {
  purpose: 'pww-demo'
}
var apimName = 'pwwdemo-apim-${suffix}'
// Cognitive Services OpenAI User
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource aiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiAccountName
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: appInsightsName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: apimName
  location: location
  tags: tags
  sku: {
    name: 'BasicV2'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
}

resource apimOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, apim.id, openAiUserRoleId)
  scope: aiAccount
  properties: {
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
  }
}

resource backend 'Microsoft.ApiManagement/service/backends@2024-05-01' = {
  parent: apim
  name: 'pwwdemo-aoai-backend'
  properties: {
    description: 'Existing Foundry account Azure OpenAI endpoint'
    url: 'https://${aiAccountName}.openai.azure.com/openai'
    protocol: 'http'
  }
}

resource logger 'Microsoft.ApiManagement/service/loggers@2024-05-01' = {
  parent: apim
  name: 'pwwdemo-appinsights'
  properties: {
    loggerType: 'applicationInsights'
    resourceId: appInsights.id
    credentials: {
      instrumentationKey: appInsights.properties.InstrumentationKey
    }
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'azure-openai'
  properties: {
    displayName: 'Azure OpenAI (pwwdemo)'
    path: 'openai'
    protocols: ['https']
    serviceUrl: backend.properties.url
    subscriptionRequired: true
    subscriptionKeyParameterNames: {
      header: 'api-key'
      query: 'subscription-key'
    }
  }
}

resource chatOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: api
  name: 'chat-completions'
  properties: {
    displayName: 'Chat Completions'
    method: 'POST'
    urlTemplate: '/deployments/{deployment-id}/chat/completions'
    templateParameters: [
      {
        name: 'deployment-id'
        required: true
        type: 'string'
      }
    ]
    request: {
      queryParameters: [
        {
          name: 'api-version'
          required: true
          type: 'string'
        }
      ]
    }
  }
}

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('policy.xml')
  }
  dependsOn: [backend]
}

resource apiDiagnostic 'Microsoft.ApiManagement/service/apis/diagnostics@2024-05-01' = {
  parent: api
  name: 'applicationinsights'
  properties: {
    loggerId: logger.id
    alwaysLog: 'allErrors'
    sampling: {
      samplingType: 'fixed'
      percentage: 100
    }
    metrics: true
  }
}

resource product 'Microsoft.ApiManagement/service/products@2024-05-01' = {
  parent: apim
  name: 'pwwdemo-ai'
  properties: {
    displayName: 'pwwdemo-ai'
    description: 'AI gateway demo product'
    subscriptionRequired: true
    approvalRequired: false
    state: 'published'
  }
}

resource productApi 'Microsoft.ApiManagement/service/products/apis@2024-05-01' = {
  parent: product
  name: api.name
}

var consumers = ['asset-agent', 'partner-app']

resource subscriptions 'Microsoft.ApiManagement/service/subscriptions@2024-05-01' = [
  for c in consumers: {
    parent: apim
    name: c
    properties: {
      displayName: c
      scope: product.id
      state: 'active'
    }
    dependsOn: [productApi]
  }
]

resource diagSetting 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'pwwdemo-apim-to-law'
  scope: apim
  properties: {
    workspaceId: logAnalytics.id
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'GatewayLogs'
        enabled: true
      }
      {
        category: 'GatewayLlmLogs'
        enabled: true
      }
    ]
  }
}

output gatewayUrl string = apim.properties.gatewayUrl
output apimName string = apim.name
output subscriptionIds array = [for (c, i) in consumers: subscriptions[i].id]
