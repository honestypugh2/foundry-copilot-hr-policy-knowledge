# AI governance evidence demo

The governance demo adds a Python evidence layer and four Jupyter notebooks to
the existing HR-policy repository. It illustrates an AI estate overview with
drill-through to native control planes. It is a reporting and education surface,
not a new enforcement service or an enterprise-wide discovery product.

## Code ownership

| File | Responsibility |
| --- | --- |
| [evidence.py](../src/governance/evidence.py) | Typed assets/observations, synthetic fixtures, coverage, overview tables, exports and snapshot loading |
| [live.py](../src/governance/live.py) | Scoped Commercial inventory/configuration/log reads and explicitly gated inference |
| [governance_demo.py](../scripts/demo/governance_demo.py) | Offline/live/snapshot CLI and local exports |
| [test_governance_evidence.py](../tests/test_governance_evidence.py) | Model constraints, provenance, scope checks, invocation safety, exports and notebook execution |

The gateway wrapper reuses
[gateway_demo.call](../scripts/demo/gateway_demo.py). Published-agent calls use
the project Responses API with an existing agent reference, or the hosted
agent's published Responses endpoint. Unlike the Pattern B smoke script, these
calls do not initialize an agent or fall back to local retrieval.

## Notebook interfaces

All notebooks run independently and default to offline synthetic data. Their
Python kernel requires the optional `notebooks` dependencies, available through
`uv sync --extra notebooks`. They can run from the repository root or their
own directory. Committed notebooks contain no outputs.

| Notebook | Content |
| --- | --- |
| [01_ai_estate.ipynb](../notebooks/governance/01_ai_estate.ipynb) | Asset inventory, ownership, cloud/source provenance, coverage, optional live reads |
| [02_govern_model_access.ipynb](../notebooks/governance/02_govern_model_access.ipynb) | Two gateway consumers, subscription counters, status/usage interpretation, opt-in model calls |
| [03_follow_the_evidence.ipynb](../notebooks/governance/03_follow_the_evidence.ipynb) | Filter outcomes versus traces/alerts/risks; opt-in existing prompt and hosted endpoint calls |
| [04_governance_overview.ipynb](../notebooks/governance/04_governance_overview.ipynb) | Combined overview, explicit gaps, snapshot loading and optional local export |

`LIVE_READS` enables configuration reads only. `ALLOW_PAID_INFERENCE` enables
model requests. `ALLOW_JAILBREAK_TEST` separately selects the synthetic
prompt-injection input. No notebook grants roles, configures security plans,
marks an identity compromised, or deploys infrastructure.

## Evidence contract

An `Asset` identifies its runtime, platform, cloud, owner, source, collection
time, and evidence kind. An `Evidence` row belongs to an asset and records a
category, observation, status, source and collection time. Optional metrics
include HTTP status, total/remaining tokens, request count, latency and a request
correlation identifier. Source security signals include their count and event
time when available, distinct from collection time. Absent usage is null, not zero.

Categories are `inventory`, `control`, `usage`, `security`, and `visibility`.
Statuses describe an observation: `observed`, `attention`, `unknown`, or
`error`. They are not compliance ratings. Unknown/unavailable evidence cannot
assert an observed result. Asset IDs must be unique and every observation must
reference an asset.

| Evidence kind | Meaning |
| --- | --- |
| `synthetic` | Repository-authored illustrative data; never a tenant observation |
| `live` | Result of a service read or invocation at its recorded timestamp |
| `snapshot` | Previously live evidence loaded from a normalized export |
| `unavailable` | Missing connector or failed collection; never zero risk |
| `unverified` | Visibility or attribution not established |

Snapshot loading preserves original timestamps, sources and outcomes. It
converts only live provenance to snapshot provenance; synthetic and missing
evidence do not become verified simply because they were exported.

## Live collector scope

The collector requires `AZURE_AI_PROJECT_RESOURCE_ID` and uses Azure CLI plus
`DefaultAzureCredential`. The active CLI subscription must match the target
project; `EXPECTED_AZURE_SUBSCRIPTION_ID` and `EXPECTED_AZURE_TENANT_ID`, when
set, add explicit context constraints. Only `AzureCloud` is supported.

The live view reads:

- Project-resource-group resource names, IDs and types through a projected
  `az resource list`. Tags and resource properties are not exported.
- Foundry agent definitions through `AIProjectClient.agents.list()`. Definitions
  do not establish publication, identity association, or telemetry delivery.
- Existing [Agent 365 preflight](../scripts/demo/agent365_preflight.py) checks.
  Hosted principal object IDs are optional, explicit inputs; omitted identity
  coverage remains unknown.
- One hour of gateway request counts grouped by HTTP status, scoped by APIM
  resource ID, when the resource group contains exactly one Log Analytics
  workspace. No request or response payloads are queried.
- Active Defender for Cloud alert metadata, read at resource-group scope and
  matched to the Foundry account's resource identifiers. The projection contains
  only alert ID, status, severity, event time and resource identifiers; no
  suspicious-prompt evidence or alert bodies. Account-level source alerts are
  never assigned to a prompt/hosted agent or treated as Agent 365 risk.

Scope/root inventory failures stop collection. Agent/configuration/log-query
failures produce explicit error/unavailable rows while preserving other
evidence. Raw service exception text is not exported; the failed operation and
exception type identify the missing coverage. Owners remain `Unassigned`;
resource metadata is not a verified ownership source.

The collector does not read Agent 365 risk feeds, agent-attributed Defender risks, Purview
findings, Sentinel incidents, Copilot Studio inventory, or browser-AI discovery.
Those connectors are outside the implemented coverage, not implied by a
successful Azure resource read.

## CLI

```bash
python -m scripts.demo.governance_demo
python -m scripts.demo.governance_demo --live
python -m scripts.demo.governance_demo --live --hosted-principal-id <object-id>
python -m scripts.demo.governance_demo --export notebooks/governance/exports/example
python -m scripts.demo.governance_demo --snapshot notebooks/governance/exports/example/estate.json
```

`--live` and `--snapshot` are mutually exclusive. The default path performs no
service calls and does not load `.env`. Live mode loads the repository's
ignored `.env`. The CLI does not offer inference switches; inference is a
separate, explicit notebook/function boundary.

Exit codes: `1` for failed reads, validation/export errors, or collection-error
rows; `2` for otherwise usable output containing unknown coverage; `0` only
when neither condition is present. The bundled synthetic dataset intentionally
returns `2`. Exit `2` is not an inference failure or a zero-risk result.

## Privacy and export boundary

The live wrappers extract selected metadata, not raw HTTP bodies, prompts,
completions, access tokens, subscription keys, or connection strings.
Gateway destinations must be HTTPS Azure APIM origins before a key is sent.
Agent endpoint addresses derive from the validated Commercial project ARM ID.
Inference can incur charges; no wrapper retries to force a rate-limit result.

`export_estate` writes `estate.json` plus `overview.csv` and refuses existing
output files. CSV formula prefixes are escaped. Local exports under
`notebooks/governance/exports/` are git-ignored. They still contain resource
metadata and require appropriate handling; the schema is not a general-purpose
secret scrubber for user-authored values. Notebook outputs may also contain
organizational metadata and should not be committed.

The CSV is a possible downstream reporting input, not a deployed Power BI
report. Cross-cloud transfer, refresh, permissions, classification and licensing
are not implemented. Commercial demonstrations do not prove GCC or Azure
Government availability.

## Interpretation limits

HTTP success does not establish useful model output or telemetry delivery.
A filter block does not establish a Defender detection. A Defender detection
does not establish Agent 365 risk arrival. A request identifier is not
necessarily an OpenTelemetry trace identifier.

Agent 365 ingestion and agent-attributed jailbreak risk remain unverified.
The overview intentionally shows no combined risk score and never converts a
missing security feed into zero risks. Native platforms remain authoritative
for enforcement and investigation.

Related implementation references:
[Agent365Observability.md](Agent365Observability.md),
[DemoRunbook-PWW.md](DemoRunbook-PWW.md), and
[gateway_queries.kql](../scripts/demo/gateway_queries.kql).
