@description('Name of the Azure AI Search service queried by the Hosted Agent')
param searchName string

@description('Name of the Application Insights component receiving Hosted Agent telemetry')
param applicationInsightsName string

@description('Managed identity principal ID for the deployed Foundry Hosted Agent')
param hostedAgentPrincipalId string

resource search 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: searchName
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
resource hostedAgentSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, hostedAgentPrincipalId, searchIndexDataReaderRoleId)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: hostedAgentPrincipalId
    principalType: 'ServicePrincipal'
  }
}

var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'
resource hostedAgentMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, hostedAgentPrincipalId, monitoringMetricsPublisherRoleId)
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleId)
    principalId: hostedAgentPrincipalId
    principalType: 'ServicePrincipal'
  }
}
