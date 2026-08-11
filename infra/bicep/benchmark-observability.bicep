@description('Azure region for monitoring resources')
param location string

@description('Stable resource token used in monitoring resource names')
param resourceToken string

@description('Log Analytics workspace resource ID containing benchmark traces')
param workspaceResourceId string

@description('Application Insights resource ID used as the workbook source')
param applicationInsightsResourceId string

@description('Optional email receiver for benchmark alerts. Alerts remain visible in Azure Monitor when omitted.')
param alertEmail string = ''

module actionGroup 'br/public:avm/res/insights/action-group:0.8.0' = {
  params: {
    name: 'ag-benchmark-${resourceToken}'
    groupShortName: 'hrbench'
    enableTelemetry: false
    emailReceivers: empty(alertEmail) ? [] : [
      {
        emailAddress: alertEmail
        name: 'benchmark-operator'
        useCommonAlertSchema: true
      }
    ]
  }
}

var benchmarkScopeQuery = 'AppDependencies | where Name == "benchmark.case" | where isnotempty(tostring(Properties["app.benchmark.experiment.id"]))'

module failureAlert 'br/public:avm/res/insights/scheduled-query-rule:0.6.0' = {
  params: {
    name: 'alert-benchmark-failures-${resourceToken}'
    alertDisplayName: 'HR policy benchmark failures'
    alertDescription: 'One or more controlled benchmark cases failed during the evaluation window.'
    scopes: [workspaceResourceId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    severity: 2
    actions: {
      actionGroupResourceIds: [actionGroup.outputs.resourceId]
      customProperties: {
        workload: 'hr-policy-benchmark'
        evidence: 'controlled-experiment'
      }
    }
    criterias: {
      allOf: [
        {
          query: '${benchmarkScopeQuery} | summarize AggregatedValue = countif(Success == false)'
          timeAggregation: 'Count'
          metricMeasureColumn: 'AggregatedValue'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            minFailingPeriodsToAlert: 1
            numberOfEvaluationPeriods: 1
          }
        }
      ]
    }
    enableTelemetry: false
  }
}

module latencyAlert 'br/public:avm/res/insights/scheduled-query-rule:0.6.0' = {
  params: {
    name: 'alert-benchmark-latency-${resourceToken}'
    alertDisplayName: 'HR policy benchmark latency regression'
    alertDescription: 'Benchmark p95 client-boundary latency exceeded 30 seconds during the evaluation window.'
    scopes: [workspaceResourceId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT30M'
    severity: 3
    actions: {
      actionGroupResourceIds: [actionGroup.outputs.resourceId]
      customProperties: {
        workload: 'hr-policy-benchmark'
        slo: 'p95-latency'
      }
    }
    criterias: {
      allOf: [
        {
          query: '${benchmarkScopeQuery} | summarize AggregatedValue = percentile(DurationMs, 95)'
          timeAggregation: 'Average'
          metricMeasureColumn: 'AggregatedValue'
          operator: 'GreaterThan'
          threshold: 30000
          failingPeriods: {
            minFailingPeriodsToAlert: 1
            numberOfEvaluationPeriods: 1
          }
        }
      ]
    }
    enableTelemetry: false
  }
}

var workbookTemplate = replace(
  loadTextContent('../workbooks/hr-policy-benchmark.workbook.json'),
  '__WORKSPACE_ID__',
  workspaceResourceId
)

resource benchmarkWorkbook 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid(resourceGroup().id, 'hr-policy-benchmark')
  location: location
  kind: 'shared'
  properties: {
    category: 'workbook'
    displayName: 'HR Policy Benchmark'
    description: 'Latency, failures, response models, and service-reported token usage for controlled benchmark runs.'
    serializedData: workbookTemplate
    sourceId: applicationInsightsResourceId
    version: 'Notebook/1.0'
  }
}

output actionGroupResourceId string = actionGroup.outputs.resourceId
output workbookResourceId string = benchmarkWorkbook.id
