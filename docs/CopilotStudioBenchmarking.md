# Benchmarking through Copilot Studio

Complete each pattern's setup in
[Pattern Setup, Code Ownership, and Benchmark Guide](PatternSetupAndBenchmarkGuide.md)
before using this document. This guide measures five isolated, published agents;
it does not provision their Azure or Copilot Studio dependencies.

Run end-to-end measurements against the real, published Copilot Studio agents
configured for each pattern. The intentionally empty `TestAgent` is only an
extension synchronization smoke test and is not a benchmark target. This
repository owns the benchmark dataset, manifests, Direct Line runner, normalized
evidence, and cross-pattern reports. The extension manages exported agent source;
it is not a Python invocation API.

## Measurement model

Run every architecture twice when possible:

1. Run its direct repository adapter to measure the component boundary.
2. Run the same cases through each published pattern agent to measure the complete
  Copilot Studio experience.

The Copilot Studio run records client wall time, answer text, exposed citations,
conversation/activity IDs, and raw Direct Line activities. Copilot-owned model
tokens, internal tool duration, and orchestration stages remain unavailable unless
the service explicitly returns them. Do not subtract direct-adapter latency from
end-to-end latency and label the result as Copilot overhead.

### What the "front door" measures — execution order and latency

The `CopilotStudioAdapter`
([src/benchmarking/adapters/copilot_studio.py](../src/benchmarking/adapters/copilot_studio.py))
times a **single opaque boundary**: it starts a timer, sends the question over
**Direct Line**, awaits the final response, and stops the timer. The measured
order is:

```
client → Direct Line send → [ Copilot Studio orchestration (opaque) ] → final activity → client
                                    ├─ generative answer (model)
                                    ├─ knowledge call (Azure AI Search / Foundry IQ)
                                    ├─ tool call (REST /api/lookup)
                                    └─ connected-agent call (Foundry external agent)
```

Everything inside the brackets is **Microsoft-managed and not individually
timed**. The adapter records `client_wall_time_ms` as `measured` and
`service_elapsed_time_ms` as `unavailable` (`NOT_EXPOSED`). So:

- **Yes** we can report how long the whole front door takes (client wall time,
  p50/p95/p99) and its reliability.
- **No** we cannot, from Direct Line, break out how long Copilot Studio spent
  calling the Foundry external agent vs. a REST tool vs. knowledge. Direct Line
  activities are captured (`activity[]`) but do not carry per-step billable or
  timing telemetry for those sub-calls.

To attribute per-step latency you must measure the **component** boundary
directly (this repo already does): the Foundry agent + MCP path via
`direct-pattern-b` (`foundry_responses_agent_mcp`), the REST tool via
`direct-pattern-c` (`deterministic_lookup`) and its load test, and knowledge via
`direct-pattern-a` / `direct-pattern-a2`. Compare the front-door wall time to the
sum of component times as a **qualitative** overhead observation only — never
subtract one boundary from another and label the difference "Copilot overhead."


## Generate synthetic data and the benchmark dataset

Every pattern — Copilot Studio, Foundry, Agent Framework, and the direct Azure
AI Search adapters — is measured against the **same** synthetic corpus and the
**same** question dataset, so a cross-pattern difference is attributable to the
architecture, not the data.

**1. Synthetic corpus (the grounding documents).** The knowledge base ships as
fully synthetic, non-confidential HR policy files with sanitized IDs. Regenerate
or refresh it before indexing:

```bash
uv run python scripts/generate_synthethic_docs.py            # rebuild both sets
uv run python scripts/generate_synthethic_docs.py --dry-run  # preview changes
```

It rebuilds the flat set (`data/knowledge_base/ASK HR Knowledge/`) and the
folder-per-document lab set (`data/knowledge_base_lab/`), preserving the
`{policy_number} - {title} ({synthetic_id}).{ext}` naming and the original mix
of `.docx/.doc/.pdf/.xlsx` formats. Record the resulting corpus fingerprint and
reuse it across every pattern's manifest. Index it with the same index
configuration for all patterns (see [Walkthrough.md](Walkthrough.md) §4).

**2. Question dataset (the cases and expected answers).** The benchmark cases are
human-authored and version-controlled under `experiments/datasets/` — see
[experiments/datasets/README.md](../experiments/datasets/README.md). The
correlated release set is:

| File | Role |
| --- | --- |
| `copilot-hr-policy-release-v2.json` | The nine cases (seven quality + one prompt-injection + one secret-disclosure), used for the Direct Line run and the native replay |
| `copilot-hr-policy-release-v2-evaluation.json` | Grader spec (deterministic source/refusal/permission assertions + judge prompts) |
| `copilot-hr-policy-release-v2-copilot-studio.csv` | The `Question,Expected response` import file for a Copilot Studio **Single response** evaluation |

Use all nine questions for both the Direct Line benchmark and the Copilot Studio
native replay. The same JSON dataset feeds the Foundry, Agent Framework, and
direct-search lanes, which is what makes the judge scores comparable. There is no
generator for the question set — cases are curated by hand and reviewed so the
`gold-` calibration subset and deterministic assertions stay authoritative when
the LLM judge disagrees.

### Equal-depth instructions for the other lanes

This document is the Copilot Studio front-door lane. The other lanes have
setup + synthetic-data + evaluation instructions of equivalent depth:

| Lane | Setup + run | Evaluation |
| --- | --- | --- |
| **Copilot Studio front door** (A, A2, B/Hosted front doors, C) | This document (§Configure agents → §Run all five patterns) | This document (§Run native Copilot Studio Evaluation) |
| **Foundry prompt agent (B) & deployed Hosted agent** | [Walkthrough.md](Walkthrough.md) §3–§6, §9; [AgentArchitecturePaths.md](AgentArchitecturePaths.md) | [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md); local re-run for per-token cost |
| **Agent Framework local (Hosted: tool / context-semantic / context-agentic)** | [Walkthrough.md](Walkthrough.md) §9; [AgentArchitecturePaths.md](AgentArchitecturePaths.md) §Hosted retrieval modes | [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md) §Current Cost Evidence (priced runs) |
| **Direct Azure AI Search adapters** (component boundary) | [Walkthrough.md](Walkthrough.md) §4; [DataPipelineAndTesting.md](DataPipelineAndTesting.md) | Retrieval-only — quality is N/A by design; grade the front-door lane that consumes it |

## Configure one real agent per pattern

Use separate agents so each end-to-end run exposes exactly one retrieval path.
Do not put all tools on one benchmark agent and ask the orchestrator to choose;
that measures routing accuracy in addition to the pattern and can send a query
down the wrong path.

| Pattern agent | Required configuration |
| --- | --- |
| **A** | Add only `hr-policy-index` as an Azure AI Search knowledge source. Do not add a Foundry agent, Foundry IQ tool, or REST lookup tool. |
| **A2** | Add only `hr-knowledge-base` through **Build → Tools → Foundry IQ**. |
| **B** | Add only the `HRPolicyAgent` Microsoft Foundry external agent. |
| **C** | Add only the deterministic lookup REST tool from `copilot/openapi-lookup-v2.json`. |
| **Hosted** | Add only the deployed `hr-policy-agent` Microsoft Foundry external agent. |

> **Front-door display-name → AgentId → pattern crosswalk.** The Copilot Studio
> display names are intentionally arbitrary (renaming forces a re-publish), so map
> each front door by its connected external `AgentId`, **not** its name:
>
> | Front door (display name) | Harness | Model | Connected AgentId | Pattern |
> | --- | --- | --- | --- | --- |
> | Ask HR Policy Agent | Standard | Claude Sonnet 4.6 | — (Search knowledge) | A |
> | Ask HR Policy Agent A2G | GitHub Copilot | Claude Sonnet 4.6 | — (Foundry IQ tool) | A2 |
> | Ask HR Policy Agent B foundry | Standard | Claude Sonnet 4.6 | `HRPolicyAgent` | B |
> | Ask HR Policy Agent C | Standard | Claude Sonnet 4.6 | — (REST lookup) | C |
> | Ask HR Policy Agent B | Standard | Claude Sonnet 4.6 | `hr-policy-agent` | Hosted |
> | Ask HR Policy Agent Hosted | GitHub Copilot | Claude Sonnet 4.6 | `hr-policy-agent` | Hosted (harness-comparison lane) |

Give all five agents the same top-level HR instructions and set the Copilot
Studio model identically across them. **Model parity:** this project pins
**Claude Sonnet 4.6** (GA) on every front door — it is one of the models
available in **both** harnesses (standard and GitHub Copilot), so A2 can match
A/B/C/Hosted. The harness differs by pattern — the standard harness for A / B /
C / Hosted and the GitHub Copilot harness for A2 — so record both in the manifest
`answer_model` field as `<harness>:<model>`
(`microsoft_managed_standard_harness:claude-sonnet-4.6` or
`github_copilot_harness:claude-sonnet-4.6`) rather than a pinned Foundry
deployment. See
[AgentArchitecturePaths.md](AgentArchitecturePaths.md) "Model parity and
confounds" for why Copilot Studio cost/quality is not directly comparable to the
Foundry patterns' per-token, pinned `gpt-5-mini`. Send the original dataset
question unchanged. The difference between agents must be the configured
knowledge/tool path, not a `/benchmark` prefix.

> **Pattern A model boundary.** Pattern A is "direct Search" because it has no
> repo-owned backend agent or answer-model call. Copilot Studio still uses its
> selected model to synthesize an answer from Search results. A truly model-free
> Search baseline exists only in the direct repository adapter, outside Copilot
> Studio.

For auditable citation grading, have benchmark routes preserve native structured
citations when available and end policy claims with this fallback format:

```text
[Policy 50010 - Paid Time Off]
```

For each real pattern agent in its VS Code extension window:

1. Use **Get changes** before editing.
2. Verify its instructions, selected knowledge/tool, and exported model setting.
3. Use **Preview changes** and verify only that pattern agent changed.
4. Use **Apply changes** to synchronize the development agent.
5. Publish the agent to the Mobile app channel in Copilot Studio. Applying source
   changes does not prove that the channel is running the new published version.

Use non-production copies of the real agents for repeatable benchmark runs.

## Configure Direct Line

In Copilot Studio, open **Channels > Mobile app** and copy the Token Endpoint.
Each agent has a distinct schema name and token endpoint. Pass them explicitly to
the benchmark CLI; this avoids silently measuring whichever agent happens to be
in `.env`:

```dotenv
COPILOT_STUDIO_ENVIRONMENT_ID=<power-platform-environment-id>
COPILOT_STUDIO_AGENT_SCHEMA=<pattern-agent-schema-name>
COPILOT_STUDIO_TOKEN_ENDPOINT=<pattern-agent-mobile-app-token-endpoint>
```

The benchmark CLI loads `.env`. Never commit the token endpoint or tenant-specific
agent identifiers.

## Generate versioned manifests

Generate one manifest per real agent after applying or exporting its source. The
generator hashes that agent's files into `configuration_version` and records its
name and selected Copilot Studio model.

```bash
source .venv/bin/activate
python -m scripts.generate_copilot_benchmark_manifests \
  --pattern A \
  --agent-name 'Ask HR Policy Agent - A' \
  --agent-source '/path/to/Ask HR Policy Agent - A' \
  --dataset experiments/datasets/copilot-hr-policy-v1.json \
  --output-dir experiments/manifests/copilot-studio \
  --corpus-fingerprint '<current-corpus-fingerprint>' \
  --index-fingerprint '<current-index-fingerprint>' \
  --model-deployment 'microsoft_managed_standard_harness:claude-sonnet-4.6' \
  --repetitions 3
```

`--model-deployment` records the `answer_model` provenance marker, not a pinned
Foundry deployment. Use the `<harness>:<model>` marker for the lane —
`microsoft_managed_standard_harness:claude-sonnet-4.6` for A, C, and the B/Hosted
front doors, or `github_copilot_harness:claude-sonnet-4.6` for A2. The Copilot
Studio model is selectable and recorded (this project uses **Claude Sonnet 4.6**,
GA), but Copilot Studio is billed in per-message Credits, so it never joins
Foundry's per-token cost axis. Keep the marker in sync with the model actually
selected and published in the maker portal.

Repeat for A2, B, C, and Hosted using each exported agent directory. Use
fingerprints from the same corpus and index configuration. Regenerate a manifest
after any model, prompt, action, knowledge, corpus, index, agent, or deployment
change.

## Run all five patterns

Run against non-production copies of the real agents. Start with one
case/repetition, then run the complete dataset. This example runs Pattern A;
repeat it with each pattern's manifest, schema, and token endpoint.

Before every live Azure, Search, Foundry, Copilot Studio, `az`, or `azd`
operation, activate the project environment and run the fail-closed identity
preflight. It verifies the token tenant and principal plus the active Azure CLI
subscription against the pinned `EXPECTED_AZURE_*` values in `.env`:

```bash
source .venv/bin/activate
python -m src.config.azure_identity
```

Do not continue when the command returns nonzero. Authenticate the intended
Admin Diamond account directly in the terminal, rerun the preflight, and proceed
only after all three identifiers match.

```bash
source .venv/bin/activate
python -m src.config.azure_identity && \
python -m src.benchmarking.cli \
  --manifest experiments/manifests/copilot-studio/copilot-ask-hr-policy-agent-a.json \
  --cases experiments/datasets/copilot-hr-policy-v1.json \
  --output-dir experiments/reports/copilot-studio/a \
  --copilot-studio \
  --copilot-environment-id '<power-platform-environment-id>' \
  --copilot-agent-schema '<pattern-a-agent-schema>' \
  --copilot-token-endpoint '<pattern-a-mobile-app-token-endpoint>'
```

Each case starts a fresh Direct Line conversation to avoid cross-case memory.
Warmups and measured repetitions come from each manifest. Keep concurrency at one
for controlled comparison; use the separate load harness for capacity testing.

## Re-run checklist: front-door model change

Changing a Copilot Studio front-door model is a **draft edit** — the published
channel (Direct Line token endpoint) keeps serving the old model until you
publish. To make a model change measurable and valid:

1. **Change the model** in the maker portal (Overview → *Select your agent's
   model* → Claude Sonnet 4.6) and **Publish** the agent. Applying a draft change
   alone does not affect the measured channel.
2. **Confirm the published version and timestamp** before measuring — each
   revision must be published before its first measured run.
3. **Regenerate that agent's manifest.** The model change alters
   `configuration_version` and `answer_model`
   (`microsoft_managed_standard_harness:claude-sonnet-4.6`), so the old manifest
   no longer matches.
4. **Re-run only the changed lane** over Direct Line; leave the `gpt-5-mini`
   component/Hosted bundles untouched.

For the current parity pass, only the **Hosted** front door (`Ask HR Policy Agent
B` → AgentId `hr-policy-agent`) changed from GPT-4.1 to Claude Sonnet 4.6, so only
the Hosted front-door Direct Line lane needs a re-run and a new dated manifest.
The other four (A, A2, B foundry, C) are already published on Claude Sonnet 4.6 —
confirm each one's *published* model is Claude Sonnet 4.6 and re-run any whose
published revision predates the model selection.

> **The Hosted front door also works on the GitHub Copilot harness.** A second
> agent (`Ask HR Policy Agent Hosted`, GitHub Copilot harness, Claude Sonnet 4.6)
> reaches the same deployed `hr-policy-agent`. This is a legitimate,
> architecturally-justified **extra** lane, not a replacement: keep the
> **standard** harness as the canonical Hosted front door (thin pass-through,
> parity with Pattern B, message billing), and record the GitHub Copilot lane as
> an explicit **harness comparison** — same backend agent and `gpt-5-mini` model,
> only the harness differs. Remarks:
>
> - The GitHub Copilot harness is **agentic** (it plans and calls your deployed
>   agent as a connected sub-agent), so expect materially higher latency (tens of
>   seconds of planning) and **Process-Agent Credit** billing, versus the standard
>   harness's lightweight forward and message billing.
> - Its native evaluation supports **Compare meaning** (pass score `70`), the same
>   method as the standard-harness agents — so the Compare-meaning scores are
>   method-comparable. The remaining difference is the **harness** itself, so label
>   any delta a harness effect, not a pattern or eval-method effect.
> - Because everything except the harness is held constant, this lane cleanly
>   isolates **harness overhead** — a strong illustration of Rule 1 (measure the
>   boundary) and Rule 2 (the harness isn't free). Label it a harness A/B, not a
>   sixth pattern.

## Cost lane — Copilot Studio Credits

Copilot Studio bills in **per-message Copilot Credits**, not tokens, and exposes
no stable public per-agent consumption REST API. The cost lane therefore has two
automated halves, mirroring the Foundry lane's estimate-then-reconcile pattern
(estimated per-token USD reconciled against Azure Cost Management):

**1. Forward estimate (automated).** A deterministic estimate from the published
Credit rate card × each agent's known feature mix — the same basis as the
[Microsoft Copilot Studio agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/):

```bash
python -m src.benchmarking.copilot_credits_cli estimate --pattern C --messages 35 \
  --output experiments/reports/decision-system-20260811/copilot-front-door/c/release-v2/credits-estimate.json
```

Rate card: [`experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json`](../experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json)
(classic answer 1, generative answer 2, agent action 5, tenant-graph grounding 10).
Feature mix: [`experiments/pricing/copilot-studio-credits-feature-mix.json`](../experiments/pricing/copilot-studio-credits-feature-mix.json)
(e.g. Pattern C ≈ generative answer + one agent action for the REST tool = 7
Credits/message; agent-action counts are marked `uncertain` because Direct Line
does not expose a per-message billable-event breakdown).

**2. Billed reconciliation (authoritative).** Read actual Credits in the Power
Platform admin center → **Licensing → Copilot Studio → Environments** (Copilot
credit consumption grid), or Copilot Studio → **Operate → Cost**. Export the grid
to a CSV with `agent,credits[,period,meter]` columns and reconcile:

```bash
python -m src.benchmarking.copilot_credits_cli reconcile --pattern C --messages 35 \
  --consumption ~/Downloads/copilot-studio-consumption.csv \
  --output experiments/reports/decision-system-20260811/copilot-front-door/c/release-v2/credits-reconciliation.json
```

Reconciliation reports estimated vs billed Credits and the delta; the billed
figure is authoritative. **Bring-your-own-model note:** for Pattern B and the
Hosted front door the connected **Foundry** model's tokens are billed on the
Azure per-token USD lane **in addition** to these Credits — keep the two lanes
separate and never sum them.

## Validate before comparison

For each report, verify:

- `aggregate.provenance.measurement_boundary` is
  `copilot_studio_direct_line`.
- `configuration_version` is identical across the five manifests when the same
  applied `TestAgent` revision was used.
- The manifest and token endpoint identify the intended real pattern agent.
- The response used that agent's only configured knowledge/tool path; inspect
  raw `activity` to confirm it.
- Citations contain the expected policy numbers. A missing structured citation
  or explicit `[Policy ...]` marker is scored as missing evidence.
- Each agent revision was published before its first measured run.

Direct and Copilot Studio results may be shown side by side, but only rows with
the same dataset, corpus/index fingerprints, region, deployment versions, and
run conditions are eligible for architecture recommendations.

## Verify Ask HR as Pattern A

Agent identity, invocation, and architecture isolation are separate proofs. For
`Default_AskHRPolicyAgent`, retain all three before labeling a result Pattern A:

| Proof | Evidence | Current verification method |
| --- | --- | --- |
| Agent identity | The Mobile app token endpoint contains `botsbyschema/Default_AskHRPolicyAgent/`, and the manifest names the same schema. | Machine-verifiable from local configuration and the sanitized manifest; never publish the token endpoint. |
| Agent invocation | Every measured row has a distinct Direct Line conversation ID, and report provenance is `copilot_studio_direct_line`. | Machine-verifiable from the front-door result bundle. |
| Pattern A isolation | The agent has only `hr-policy-index` under **Knowledge**, with no Foundry IQ, external-agent, or REST lookup tools that can answer HR policy questions. | Manually verify in the authenticated Copilot Studio UI and record the agent version and publication time. |

Identity and successful Direct Line responses do not prove the third condition.
Until the Knowledge and Tools configuration is inspected, label the evidence
"Ask HR front door, Pattern A configuration pending UI verification."

## Run native Copilot Studio Evaluation

Direct Line benchmark traffic does not automatically create test sets or results
on the **Evaluation** page. Native evaluation is a separate replay owned by
Copilot Studio. Use it for response quality, while retaining the Direct Line
bundle as the controlled latency/reliability evidence.

> **Native evaluation works only for self-contained standard-harness agents.**
> Patterns **A** and **C** evaluate natively (Compare meaning, pass score `70`).
> The standard-harness **B** and **Hosted** front doors connect to an *external*
> Foundry agent, and native Copilot Studio Evaluation **returns an Error across
> that external-agent hop** — grade B and Hosted at the **Foundry deployed-agent
> boundary** instead (their answers are synthesized there on `gpt-5-mini`). The
> **GitHub Copilot**-harness Hosted front door does evaluate (it treats the
> deployed agent as a connected sub-agent), including **Compare meaning** — so its
> quality is method-comparable to A/C; label any gap a harness effect, since the
> model (Claude Sonnet 4.6) and backend (`gpt-5-mini`) are held constant.

### One-time authenticated setup

1. Open the authenticated `Ask HR Policy Agent` and confirm the Pattern A
   isolation checks above. Capture the published version, publication time, and
   screenshots of **Knowledge** and **Tools**.
2. Go to **Evaluation**, select **New evaluation**, then **Single response**.
3. Import
   `experiments/datasets/copilot-hr-policy-release-v2-copilot-studio.csv`.
   Its exact columns are `Question` and `Expected response`. It contains the
   same seven quality and two security cases as the release-v2 Direct Line set.
4. Name the test set exactly `Ask HR Pattern A release-v2`. Keep this stable;
   automation resolves an exact active name and fails on duplicates.
5. Keep **General quality**, add **Compare meaning**, and set its per-case pass
   score to `70`. This is the project threshold, not a Microsoft SLO. Expected
   responses are present for all nine cases.
6. Select the user profile whose permissions match the intended employee
   experience. Save the test set and run it once manually to validate all nine
   cases and both methods before enabling automation.
7. Capture the Power Platform Environment ID, Dataverse Bot ID, test-set ID,
   and optional Microsoft Copilot Studio connection ID. The Bot ID is not the
   agent schema name used by Direct Line.

### Automate a real Evaluation run

The Power Platform Evaluation API and the Microsoft Copilot Studio connector
start the standard harness. Their runs appear in **Evaluation > Recent results**.
This is the supported bridge; sending Direct Line messages still does not
populate that page.

For the repository runner, register a single-tenant public client in the Admin
Diamond tenant. Add the **Power Platform API** resource
`8578e004-a5c6-46e7-913e-12f58912df43`, configure its delegated Copilot Studio
maker permissions, and grant tenant admin consent. The tenant's prior `403`
identified `CopilotStudio.MakerOperations.Read` and `All.All.ReadWrite` as the
missing delegated permissions. Do not add a client secret; the runner uses
device-code authentication and verifies that the resulting token has the pinned
Admin Diamond tenant and principal before making a request.

Configure nonsecret identifiers locally:

```dotenv
COPILOT_STUDIO_ENVIRONMENT_ID=<power-platform-environment-id>
COPILOT_STUDIO_BOT_ID=<dataverse-bot-id>
POWER_PLATFORM_EVALUATION_CLIENT_ID=<delegated-public-client-app-id>
```

Run the identity preflight and trigger the existing published-agent test set:

```bash
source .venv/bin/activate
python -m src.config.azure_identity && \
python -m src.benchmarking.copilot_evaluation_cli run \
  --test-set-name 'Ask HR Pattern A release-v2' \
  --expected-case-count 9 \
  --run-name 'pattern-a-release-v2-<experiment-id>' \
  --output experiments/reports/<experiment-id>/copilot-native-run.json
```

Complete the device-code sign-in as the same Admin Diamond principal. The
command resolves one active test set with exactly nine cases, runs the published
agent, polls to `Completed`, and saves a sanitized result containing correlation
IDs, timestamps, case states, and metric statuses. It omits tokens, grader
explanations, and grader payload text. Only one Evaluation test set can run at a
time.

The no-code alternative is a Power Automate flow using the Microsoft Copilot
Studio connector under the Admin Diamond connection:

1. Use **Get Agent Test Sets** and require one active `Ask HR Pattern A
   release-v2` set with nine cases.
2. Call **Evaluate Agent** with that test set and the intended user profile.
3. Poll **Get Agent Test Run Details** until the state is `Completed`; fail the
   flow for every other terminal state.
4. Persist the sanitized run details and run ID in approved project storage.

This connector path avoids custom token handling and is the preferred immediate
automation when delegated app permissions are not yet approved.

### Export, assert, and attach

The Evaluation API exposes test-case IDs and grader metrics, but not the question
and actual response fields required by the repository's deterministic citation,
refusal, and security checks. After the run appears in **Recent results**:

1. Inspect every failure and at least one passing case. Open **Show activity
   map** and verify the expected `hr-policy-index` resource was used with no
   competing Foundry IQ, external-agent, or REST lookup path.
2. Use **Export test results**. The importer accepts both portal layouts:
   the older one-row-per-method columns (`Question`, `Expected response`,
   `Test method`, `Passing score`, `Agent response`, `Test result`, and
   `Analysis`) and the current one-row-per-question layout with
   `conversationId`, question/response columns, and paired `testMethodType_*`,
   `result_*`, `passingScore_*`, and `explanation_*` columns.
3. Import and attach it to the correlated Direct Line report:

```bash
source .venv/bin/activate
python -m src.benchmarking.copilot_evaluation_cli import \
  --export-csv '<downloaded Ask HR Pattern A release-v2.csv>' \
  --native-run experiments/reports/<experiment-id>/copilot-native-run.json \
  --cases experiments/datasets/copilot-hr-policy-release-v2.json \
  --evaluation-spec experiments/datasets/copilot-hr-policy-release-v2-evaluation.json \
  --experiment-id '<experiment-id>' \
   --dataset-version '<exact dataset_version from the matching manifest>' \
  --environment-id '<power-platform-environment-id>' \
  --bot-id '<dataverse-bot-id>' \
  --test-set-id '<test-set-id>' \
  --output experiments/reports/<experiment-id>/copilot-native-evaluation.json \
  --report experiments/reports/<experiment-id>/<experiment-id>.report.json
```

The importer fails closed on the wrong environment, bot, test set, case count,
question, missing method, duplicate method, noncompleted case, `Invalid`, or
`Error`. To retain a completed but nonqualifying run, add
`--archive-nondecisive`; this preserves `Error` and `Invalid` in each method's
denominator and records explicit release blockers. It does not convert those
statuses to failures or passes. The importer requires API and CSV status counts
to agree. It hashes questions and responses in the normalized artifact,
calculates deterministic quality/security and category slices, and records
`separate_same_published_agent_testset_replay`. It does not claim that native
Evaluation graded the timed Direct Line responses. Refreshing the benchmark
workbench then shows the native method rates and run/test-set IDs alongside the
deterministic release gates.

Native Evaluation is quality and attribution evidence, not a latency harness.
Use Direct Line client-wall-time percentiles for controlled front-door latency,
the activity map to explain routing/resource use, and Application Insights or
Monitor traces for production bottlenecks. Copilot Studio retains native results
for 89 days, so retain both the exported CSV and normalized artifact according
to project privacy and evidence-retention policy.

The GitHub Copilot agent experience is a separate production-ready harness. Its
Evaluation now supports **Compare meaning** as well as General quality, so its
Compare-meaning scores are method-comparable to the standard-harness agents. Any
remaining quality difference reflects the **harness**, not the evaluation method;
label it accordingly and hold the model and backend constant when comparing.

Themes are production-analytics evidence, not a substitute for the controlled
nine-case release set. Suggested themes require at least 50 questions with generative
answers in the previous seven days. Viewing question details also requires
Dataverse transcript storage, the environment transcript settings, and the
**Bot Transcript Viewer** role. Weekly theme suggestion and daily classification
mean a 35-observation controlled run is neither sufficient nor expected to
populate Themes immediately.

Reference guides:

- [Create a single response test set](https://learn.microsoft.com/en-us/microsoft-copilot-studio/analytics-agent-evaluation-create)
- [Automate evaluations with the Power Platform API](https://learn.microsoft.com/en-us/microsoft-copilot-studio/analytics-agent-evaluation-rest-api)
- [Trigger evaluations with connectors](https://learn.microsoft.com/en-us/microsoft-copilot-studio/analytics-agent-evaluation-automate-tools)
- [Analyze user questions by theme](https://learn.microsoft.com/en-us/microsoft-copilot-studio/analytics-themes#prerequisites)
- [Evaluate an agent in the GitHub Copilot experience](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/analytics-agent-evaluation-intro)