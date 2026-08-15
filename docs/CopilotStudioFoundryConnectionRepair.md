# Repair: Copilot Studio → Foundry connection returns empty (Pattern B / Hosted)

Runbook to fix the Pattern B and Hosted **external Microsoft Foundry agent**
front doors that connect but return **empty answers**.

## Root cause (diagnosed 2026-08-14)

Copilot Studio reaches a Foundry agent through an **Azure Bot Service** created
by the agent's *Publish → Teams & Microsoft 365 Copilot* flow. That bot
authenticates its channel with a **Microsoft App (Entra) identity** (`msaAppId`).

| Bot (`rg-hr-policy-kb-hr-demo`) | Pattern | Agent | Activity endpoint | Bot state | `msaAppId` |
| --- | --- | --- | --- | --- | --- |
| `hrpolicyagent45448` | **B** | `HRPolicyAgent` | enabled | Succeeded | `bedf7d0f-9efd-4b70-94b8-65bae2fd144e` — **deleted app ❌** |
| `hr-policy-agent80542` | Hosted | `hr-policy-agent` | enabled | Succeeded | `d4efaa98-…` (MI, wired as `SingleTenant` — mismatch) |

The Pattern B bot points at an Entra app registration that **no longer exists**,
so the channel cannot authenticate and Copilot Studio receives empty responses.
Direct agent invocation still works because that uses the caller's identity, not
the bot's.

**Not the cause:** the agents exist (`HRPolicyAgent`, `hr-policy-agent`), their
runtime identities have `Search Index Data Reader` (project MI `828c85c6`;
Hosted MI `d4efaa98`), the Activity protocol is enabled, and both bots are in
the same tenant (`8632ad35-…`). Retrieval is healthy.

## RBAC prerequisites (status)

| Grant | Identity | Status |
| --- | --- | --- |
| Foundry User (Azure AI User) | publisher `admin@diax41042041` | ✅ present |
| Foundry Project Manager | publisher | ✅ present |
| **Azure Bot Service Contributor Role** on the RG | publisher | ✅ **granted 2026-08-14** |
| Entra app-registration creation (Application Developer, or tenant default) | publisher | ⚠️ verify — the publish mints a new bot app |
| Search Index Data Reader | `HRPolicyAgent` MI `828c85c6`, Hosted MI `d4efaa98` | ✅ present |

## Repair steps

### 1. Remove the orphaned bots

The bots reference dead/mismatched app identities; let the publish flow recreate
them cleanly.

```bash
az resource delete -g rg-hr-policy-kb-hr-demo -n hrpolicyagent45448 \
  --resource-type Microsoft.BotService/botServices
az resource delete -g rg-hr-policy-kb-hr-demo -n hr-policy-agent80542 \
  --resource-type Microsoft.BotService/botServices
```

### 2. Re-publish each Foundry agent (Foundry portal)

For **`HRPolicyAgent`** (Pattern B) and **`hr-policy-agent`** (Hosted):

1. Open the agent in the Microsoft Foundry portal.
2. **Publish → Teams and Microsoft 365 Copilot** and complete the flow (choose
   **Just you** for an isolated test). This regenerates a Bot Service **and a
   valid app registration + credential**, and enables the Activity protocol.
3. Confirm the new bot resolves to a live app identity:

```bash
NEWBOT=$(az resource list -g rg-hr-policy-kb-hr-demo \
  --query "[?contains(type,'BotService')].name" -o tsv | head -1)
APP=$(az resource show -g rg-hr-policy-kb-hr-demo -n "$NEWBOT" \
  --resource-type Microsoft.BotService/botServices --query properties.msaAppId -o tsv)
az ad app show --id "$APP" --query "{appId:appId,displayName:displayName}" -o json  # must NOT error
```

### 3. Reconnect in Copilot Studio

For each standard-harness front-door agent (`Ask HR Policy Agent B` /
`Ask HR Policy Agent B foundry`, and the Hosted front door):

1. Remove the existing external agent under **Agents**.
2. **Agents → Add an agent → Connect to an external agent → Microsoft Foundry**.
3. **Create a new connection** against `AZURE_AI_PROJECT_ENDPOINT`
   (`https://cog-hr-policy-kb-zptc7utdm2gis.services.ai.azure.com/api/projects/proj-hr-policy-kb-zptc7utdm2gis`).
4. Agent Id = `HRPolicyAgent` (or `hr-policy-agent` for Hosted). Add the agent.
5. **Save and republish** the Copilot Studio agent.

### 4. Verify end to end

1. In Copilot Studio test chat, ask: *"Compare full-time and part-time PTO and
   cite both policies."* Pass = a grounded answer citing **Policy 50010** and
   **Policy 50020** (not empty).
2. Then re-run the benchmark front-door lane:

```bash
source .venv/bin/activate && python -m src.config.azure_identity  # must exit 0
python -m src.benchmarking.cli \
  --manifest experiments/manifests/copilot-front-door-b-45-20260811.json \
  --cases experiments/datasets/copilot-hr-policy-release-v2.json \
  --output-dir experiments/reports/decision-system-20260811/copilot-front-door/b \
  --copilot-studio --copilot-environment-id '<env-id>' \
  --copilot-agent-schema '<b-agent-schema>' --copilot-token-endpoint '<b-token-endpoint>'
```

Success = non-empty answers with references and a populated latency
distribution. Then attach the native Copilot Studio evaluation as for A/C.

## If it still returns empty

- **`endpoint does not support activity`** → the publish didn't enable Activity;
  redo step 2 and confirm the endpoint path ends in `.../protocols/activityprotocol`.
- **Empty but no error** → the new `msaAppId` app is missing a credential, or the
  Copilot Studio connection used a delegated identity unavailable to the eval
  runner; recreate the connection (step 3) with an account that stays authorized.
- **403 / permission** → confirm the publisher kept Foundry User + the new Bot
  Service Contributor role, and that the agent MI retains Search Index Data Reader.
