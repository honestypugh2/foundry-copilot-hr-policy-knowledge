# Native Portal Screenshots — Capture Guide & Index

Screenshots of the **Microsoft-native** surfaces (Microsoft Copilot Studio,
Microsoft Foundry, Azure) that back the five patterns. These complement the
Benchmark Workbench app screenshots in [../app/](../app/README.md) — they show
the *real* agents, evaluations, and wiring behind the numbers, which reinforces
the blog's "evidence you can defend" thesis.

> **These are not auto-captured.** They require authenticated portal access, so
> you capture them manually and save them here with the filenames below. This
> file is the index (filename → what it shows → where it's used → alt text) and
> the capture + redaction instructions.

## Redaction rules (do this on every native screenshot)

Native portals show tenant-identifying and sometimes sensitive values. Before
committing any image:

- **Crop or blur** the project/resource identifier in the breadcrumb (e.g.
  `proj-hr-policy-kb-...`, `cog-...`, subscription/resource-group GUIDs).
- **Blur owner / user names, emails, avatars** (the Copilot Studio "Owner"
  column, profile menus).
- **Never** capture secrets: Direct Line channel secrets, token endpoints,
  connection strings, API keys, `APPLICATIONINSIGHTS_CONNECTION_STRING`.
- Prefer **dark theme** and a consistent ~1600px-wide viewport to match the app
  screenshots; 2× (retina) if available.
- Keep the frame tight to the relevant panel; avoid browser chrome/bookmarks.

## The four you already have (save + redact, then they're ready)

| Save as | Native surface | Shows | Use it for | Redact |
| --- | --- | --- | --- | --- |
| `copilot-studio-agents-list.png` | Copilot Studio → Agents (New experience) | Six published Ask HR agents with **Powered by = Standard vs GitHub Copilot** | **Harness note (Rule 2)** and "five patterns are real published agents" | Owner column (already blacked) |
| `foundry-agents-list.png` | Microsoft Foundry → Build → Agents | `HRPolicyAgent` (**Prompt**, Running) + `hr-policy-agent` (**Hosted**, Running) | Pattern **B** (prompt agent) and **Hosted** are real, running | Project id in breadcrumb |
| `foundry-eval-prompt-agent.png` | Foundry → HRPolicyAgent → Evaluation | Completed **Automatic Evaluation** run | "Committed evaluation runs" / Rule 3 (native eval is supplemental) | Project id |
| `foundry-eval-hosted-agent.png` | Foundry → hr-policy-agent → Evaluation | Multiple completed evals (`curated-builtins-v1`, `curated-smoke`) | Rule 3 + the worked example's provenance | Project id |

> **Harness + model per front door (settled).** Map front doors by connected
> `AgentId`, not display name (names are intentionally arbitrary to avoid
> re-publishing):
>
> | Front door (display name) | Harness | Model | AgentId | Pattern |
> | --- | --- | --- | --- | --- |
> | Ask HR Policy Agent | Standard | Claude Sonnet 4.6 | — | A |
> | Ask HR Policy Agent A2G | GitHub Copilot | Claude Sonnet 4.6 | — | A2 |
> | Ask HR Policy Agent B foundry | Standard | Claude Sonnet 4.6 | `HRPolicyAgent` | B |
> | Ask HR Policy Agent C | Standard | Claude Sonnet 4.6 | — | C |
> | Ask HR Policy Agent B | Standard | Claude Sonnet 4.6 | `hr-policy-agent` | Hosted |
> | Ask HR Policy Agent Hosted | GitHub Copilot | Claude Sonnet 4.6 | `hr-policy-agent` | Hosted (harness-comparison lane) |
>
> The standard-harness front doors (A, B, C, Hosted) all pin **Claude Sonnet 4.6**
> (GA), matching A2 on the GitHub Copilot harness — one model, so front-door
> comparisons differ only by harness and retrieval path. Backend synthesis for B
> and Hosted is `gpt-5-mini`.

## Additional native visuals worth capturing (mapped to the blog)

Ordered by value to the post. ⭐ = highest impact.

| Save as | Native surface | Shows | Blog section it supports |
| --- | --- | --- | --- |
| `copilot-studio-a2-foundry-iq.png` ⭐ | Copilot Studio (GitHub Copilot harness) → **Build → Tools → Foundry IQ** | Adding the `hr-knowledge-base` Foundry IQ connection to the agent | Pattern A2 wiring; Rule 1 (front-door boundary) |
| `copilot-studio-knowledge-source.png` | Copilot Studio → agent → **Knowledge** | The Azure AI Search knowledge source (Pattern A) | Pattern A |
| `copilot-studio-operate-cost.png` ⭐ | Copilot Studio → **Operate → Cost** (or Power Platform admin → Licensing → Copilot Studio) | Per-message **Credits** consumption | **Rule 2** (Credits cost lane) |
| `foundry-prompt-agent-config.png` ⭐ | Foundry → HRPolicyAgent → **Details** | Prompt agent with the **MCP tool** and `tool_choice = required` | Pattern B; "force-grounded synthesis" |
| `foundry-agent-traces.png` ⭐ | Foundry → agent → **Traces** | `gen_ai` spans at the **deployed-agent boundary** | **Rule 1** (measurement boundary) |
| `foundry-eval-run-detail.png` | Foundry → Evaluation → open a run | Metric scores (relevance / groundedness) per case | **Rule 3** (judges are supplemental) |
| `foundry-knowledge-base.png` | Foundry → **Knowledge** (Foundry IQ) | The `hr-knowledge-base` config + knowledge source | Pattern A2 / one shared index |
| `foundry-model-deployment.png` | Foundry → **Deployments** | `gpt-5-mini` deployment (the pinned model) | Worked example provenance |
| `azure-search-index.png` | Azure portal → Azure AI Search → Indexes | `hr-policy-index` fields + semantic/vector config | "one index, many front doors" |
| `appinsights-agent-details.png` | Application Insights → **Agents (preview)** | Token / tool-call / latency for a run | "Reuse the native tools" (label **preview**) |
| `grafana-agent-dashboard.png` | Azure Managed Grafana | p95 / failures / throughput over time | "Reuse the native tools" |
| `cost-management-billed.png` | Azure **Cost Management** → Cost analysis | Billed Azure cost scoped to the RG | Rule 2 (per-token lane reconciliation) |

## How to capture (per portal)

**Microsoft Copilot Studio** (`https://copilotstudio.microsoft.com`)
1. Sign in; keep the **New experience** toggle on (matches your screenshots).
2. **Agents** list → the "Powered by" column is the harness (Standard vs GitHub
   Copilot). For A2 wiring: open the GitHub Copilot-harness agent → **Build →
   Tools → Foundry IQ**. For cost: **Operate → Cost**.
3. Crop the owner column; capture the panel only.

**Microsoft Foundry** (`https://ai.azure.com`)
1. Open the project → **Build → Agents** for the list; open an agent for
   **Details / Traces / Monitor / Evaluation**.
2. **Traces** shows the deployed-agent boundary spans; **Evaluation** lists the
   completed runs; **Deployments** shows the model.
3. Crop the `proj-...` breadcrumb (or blur it) before saving.

**Azure portal** (`https://portal.azure.com`)
1. Azure AI Search resource → **Indexes** (`hr-policy-index`).
2. Application Insights → **Agents (preview)** and **Performance**.
3. Azure Managed Grafana → the agent dashboard.
4. **Cost Management → Cost analysis**, scoped to the resource group.
5. Blur subscription/RG GUIDs and any resource names you don't want public.

## Where these get used

- **Blog draft** ([../../blog/benchmarking-blog-draft.md](../../blog/benchmarking-blog-draft.md)):
  harness list (Rule 2), boundary/traces (Rule 1), Credits (Rule 2), native
  tools section, evaluation (Rule 3).
- **Repo docs**: [CopilotStudioIntegration.md](../../CopilotStudioIntegration.md)
  (A2 wiring), [FoundryAgentArchitecture.md](../../FoundryAgentArchitecture.md)
  (Pattern B), [CopilotStudioBenchmarking.md](../../CopilotStudioBenchmarking.md)
  (native evaluation), [Walkthrough.md](../../Walkthrough.md) (setup steps).

Add the file, then record its **alt text** in the table above so every image
stays accessible (the blog process requires alt text on every image).
