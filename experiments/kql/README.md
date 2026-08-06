# Benchmark KQL Templates

These allowlisted templates query authoritative production telemetry. They do
not reconstruct controlled benchmark stages and are not executed by the React
client. Run them from Application Insights or an approved backend provider.

Verified against Microsoft documentation on 2026-08-03:

- Agent spans: Application Insights `dependencies`, using GenAI OpenTelemetry
  attributes stored in `customDimensions`.
- Hosted-agent requests: `requests`; join downstream spans by `operation_Id`.
- Evaluation events: `customEvents` where `name == "gen_ai.evaluation.result"`.
- Azure AI Search resource logs: `AzureDiagnostics`. The Search service must
  have diagnostic settings enabled for the target Log Analytics workspace.

Every template has an in-query time bound. Replace only the declared
parameters. Do not project prompt, completion, tool argument, tool result, or
retrieved document content. Benchmark IDs are searchable span attributes, not
metric dimensions.

Sources:

- https://learn.microsoft.com/azure/azure-monitor/app/agents-view
- https://learn.microsoft.com/azure/search/search-performance-analysis
- https://learn.microsoft.com/azure/foundry/openai/how-to/latency
