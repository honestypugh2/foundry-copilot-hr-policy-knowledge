# APIM AI gateway add-on (pwwdemo)

Stand-alone add-on, **not part of azd**. Deploys an API Management BasicV2 instance in front of the existing Foundry / Azure OpenAI account.

## What it creates
- `pwwdemo-apim-<suffix>` (BasicV2, system-assigned identity, tag `purpose=pww-demo`)
- `Cognitive Services OpenAI User` for the APIM identity on the existing account (no model API keys)
- Backend, App Insights logger, API `azure-openai` (path `openai`, header `api-key`), product `pwwdemo-ai`, subscriptions `asset-agent` and `partner-app`
- API policy ([policy.xml](policy.xml)): managed-identity auth, `llm-token-limit` (2000 TPM per subscription), `llm-emit-token-metric` (namespace `pwwdemo`, dimensions Subscription ID, API ID, Agent Name from `x-agent-name`)
- Diagnostic setting to the existing Log Analytics workspace (`GatewayLogs`, `GatewayLlmLogs`)

## Deploy
```bash
RG=rg-hr-policy-kb-hr-demo
az deployment group what-if -g $RG -f main.bicep -p main.parameters.json
az deployment group create  -g $RG -n pwwdemo-apim-gw -f main.bicep -p main.parameters.json
```

Fetch keys (write them to `.env`, never to git):
```bash
az rest --method post --url "https://management.azure.com/subscriptions/<sub>/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/<apim>/subscriptions/asset-agent/listSecrets?api-version=2024-05-01" --query primaryKey -o tsv
```

## Cleanup
```bash
az apim delete -g $RG -n <apim-name> --yes
az role assignment list --scope $(az cognitiveservices account show -g $RG -n <account> --query id -o tsv) --query "[?principalType=='ServicePrincipal' && contains(roleDefinitionName,'OpenAI User')]"  # remove the orphaned APIM assignment
```
After deletion, APIM is soft-deleted; purge with `az apim deletedservice purge --service-name <name> --location eastus2` if you need to reuse the name.
