# Pattern Code Ownership and Benchmark Guide

Build users should start with the ordered
[per-pattern guides](patterns/README.md). This document is the reference for
shared resource ownership, runtime files, smoke-test boundaries, benchmarking,
and publication lineage after a pattern has been selected.

Use it to answer four questions:

1. Which pattern should I build?
2. Which Azure resources, scripts, and source files does it use?
3. How do I smoke-test it without confusing that test with a benchmark?
4. How does it relate to the published article and the current benchmark work?

The architecture originates in the Microsoft Foundry blog post
[Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337).
The current benchmark work does not replace those five patterns. It adds a
repeatable evidence contract for comparing them.

## The shared foundation

Every pattern uses the same HR corpus and Azure AI Search index:

```text
data/knowledge_base/ASK HR Knowledge
              |
              v
one indexing pipeline (choose one)
              |
              v
hr-policy-index
  |                         |
  | direct                  | wrapped for agentic retrieval
  v                         v
A, C, Hosted       hr-knowledge-source -> hr-knowledge-base -> A2, B
```

Run these shared steps once before following a pattern-specific section.

### 1. Install and configure

```bash
uv sync
cp .env.example .env
# Set the Azure endpoints and resource identifiers in .env.
source .venv/bin/activate
```

### 2. Provision Azure infrastructure

Follow [the infrastructure walkthrough](../README.md#3-provision-azure-infrastructure).
Bicep owns control-plane resources such as Search, Foundry, model deployments,
Storage, Container Apps, identities, and RBAC. Search knowledge sources and
knowledge bases are data-plane resources and are created by Python after the
index exists.

### 3. Populate `hr-policy-index`

Choose one pipeline. Do not run both against the same environment merely to set
up another retrieval pattern.

```bash
# Recommended: Azure AI Search indexer, skillset, server-side chunking/vectorization
uv run python scripts/index_knowledge_base_integrated_vectorization.py

# Alternative: client-side Document Intelligence chunking and push indexing
uv run python scripts/index_knowledge_base_docintel_chunking.py
```

Why both scripts exist:

| File | Function | Use it when |
| --- | --- | --- |
| `scripts/index_knowledge_base_integrated_vectorization.py` | Uploads blobs, creates the data source/index/skillset/indexer, then lets Search chunk and embed documents. | Default and repeatable server-side ingestion. |
| `scripts/index_knowledge_base_docintel_chunking.py` | Parses/chunks/embeds locally and pushes documents into the same index schema. | Development, local inspection, or custom preprocessing. |
| `scripts/upload_to_blob.py` | Pre-stages files in Blob Storage only. | You want `--create-pipeline-only` or a separate upload step. It is not required by the normal integrated-vectorization run. |
| `src/config/search_config.json` | Central names, fields, semantic/vector settings, KB names, and preview API versions. | Read this when changing the shared retrieval contract. |

Pipeline internals are documented in [DataPipelineAndTesting.md](DataPipelineAndTesting.md).

## Five patterns at a glance

| Pattern | User-facing orchestrator | Retrieval target | Answer owner | Additional setup | Published-article role |
| --- | --- | --- | --- | --- | --- |
| **A** | Copilot Studio | `hr-policy-index`, classic hybrid search | Copilot Studio | Add the Search index as Knowledge | Start here: zero repo-owned agent code. |
| **A2** | Copilot Studio | `hr-knowledge-base`, agentic retrieval | Copilot Studio | Provision the KB; add Foundry IQ tool | Better retrieval without a prompt agent. |
| **B** | Foundry Agent Service, optionally called by Copilot Studio | KB MCP endpoint | `HRPolicyAgent` PromptAgent | Provision KB, MCP connection, and PromptAgent | Forced retrieval before synthesis. |
| **C** | Copilot Studio routes to REST | `hr-policy-index`, deterministic metadata lookup | No backend LLM for lookup | Run/deploy FastAPI; import lookup OpenAPI | Return the exact document URL. |
| **Hosted** | Agent Framework container, optionally called by Copilot Studio | Index directly or KB context mode | Self-hosted agent | Build/deploy `hr-policy-agent` | Own the request loop and middleware. |

The patterns are composable. A production-style Copilot can route document
locator requests to C and explanatory requests to A2 or B.

## Prompt and query map

Use this table before testing. It identifies who owns the instructions, where
the exact text is documented, and which prompt proves that the pattern is
behaving as intended.

| Pattern | Prompt/instruction owner | Exact instructions | First query to try | Expected behavior |
| --- | --- | --- | --- | --- |
| **A** | Copilot Studio | [Shared Copilot instructions](CopilotStudioIntegration.md#shared-copilot-instructions) | `What does Policy 20030 say about the probationary period?` | Answer from Policy 20030 with a native citation. |
| **A2** | Copilot Studio for the answer; Foundry IQ for retrieval | [Shared Copilot instructions](CopilotStudioIntegration.md#shared-copilot-instructions) and [A2 retrieval instructions](CopilotStudioIntegration.md#a2-prompt-contract) | `Compare the uniform and non-uniform dress code policies.` | Foundry IQ retrieves Policies 60010 and 60020; Copilot Studio synthesizes the answer. |
| **B** | `HRPolicyAgent` PromptAgent | [Pattern B prompt contract](CopilotStudioIntegration.md#pattern-b-prompt-contract) | `Explain the differences between full-time and part-time PTO and cite both policies.` | Required MCP retrieval, then a grounded answer citing Policies 50010 and 50020. |
| **C** | Copilot Studio router plus REST tool description | [Pattern C router instructions](CopilotStudioLookupRouting.md#pattern-c-router-instructions) | `Give me the link to the part-time PTO policy.` | Calls `lookupHRPolicyDocument` and returns the exact filename and URL without summarizing policy content. |
| **Hosted** | Agent Framework system prompt | [Hosted prompt contract](CopilotStudioIntegration.md#hosted-prompt-contract) | `Which IT policies govern employee devices, acceptable use, and information security?` | Calls `search_hr_policies`, then cites Policies 70070, 70010, and 70020. |

The full corpus-grounded set, including negative and ambiguous cases, is in the
[starter query catalog](CopilotStudioTestingGuide.md#starter-query-catalog).

## Pattern A: direct Search index

**Use when:** you want the smallest setup, native Copilot Studio knowledge, and
classic hybrid retrieval. No Python agent from this repository runs in the
Copilot Studio answer path.

**Setup**

1. Complete the shared indexing steps.
2. In Copilot Studio, add Azure AI Search Knowledge targeting
   `hr-policy-index`.
3. Follow [Pattern A wiring](CopilotStudioIntegration.md#pattern-a-wiring).

**Files and why they matter**

| File | Role |
| --- | --- |
| `scripts/index_knowledge_base_*.py` | Creates/populates the index Pattern A queries. |
| `src/search/integrated_vectorization_search.py` | Repository-side equivalent for direct Search calls and smoke tests; it is not invoked by Copilot Studio's native connector. |
| `scripts/demo/test_pattern_a.py` | One live direct-Search smoke test. It does not measure Copilot Studio end to end. |
| `src/benchmarking/adapters/direct_search.py` | Normalizes direct Search results for controlled experiments. |

**Smoke test**

```bash
uv run python -m scripts.demo.test_pattern_a \
  -q "Compare full-time and part-time PTO."
```

**Copilot Studio prompt:** Paste the
[shared Copilot instructions](CopilotStudioIntegration.md#shared-copilot-instructions),
then try `What does Policy 20030 say about the probationary period?`. Expect a
Policy 20030 answer with a native citation card.

## Pattern A2: Copilot Studio directly to Foundry IQ

**Use when:** you want agentic query planning and reranking but do not want a
Foundry PromptAgent between Copilot Studio and the knowledge base.

**Setup**

```bash
uv run python -m src.agents.create_foundry_agent
```

That command creates `hr-knowledge-source`, `hr-knowledge-base`, the project MCP
connection, and `HRPolicyAgent`. A2 uses only the knowledge base; the PromptAgent
created by the shared command is not in its request path.

In Copilot Studio select **Build -> Tools -> Foundry IQ**, create an Entra ID
Integrated connection, select `hr-knowledge-base`, and add it to the agent.
Follow the [A2 click path](CopilotStudioIntegration.md#pattern-a2-wiring-github-copilot-harness--foundry-iq).

Do not substitute the generic **Foundry IQ Knowledge Retrieval (API)** connector
action for the picker. In the affected surface that action exposes no retrieval
body input or retains hidden sample bindings. It fails with HTTP 400 or targets
the wrong knowledge base and API version. If the dedicated **Foundry IQ** card,
endpoint connection form, or
knowledge-base picker isn't available in the current tenant, Pattern A2 can't be
configured through the supported Copilot Studio UI. The **Azure - Foundry IQ**
API and MCP connector actions aren't substitutes because their Inputs don't
establish the Search-service binding. Follow the escalation and temporary
alternatives in the
[A2 fallback](CopilotStudioIntegration.md#a2-fallback-when-the-dedicated-foundry-iq-picker-is-unavailable).

**Files and why they matter**

| File | Role |
| --- | --- |
| `src/agents/create_foundry_agent.py` | Defines and upserts the shared Search knowledge source/base. |
| `src/config/search_config.json` | Controls KB model, retrieval instructions, source fields, output mode, and API version. |
| `src/benchmarking/adapters/knowledge_base.py` | Normalizes a direct KB retrieve boundary for controlled evidence. |
| `docs/CopilotStudioIntegration.md` | Owns the interactive Copilot Studio wiring steps. |

There is no `scripts/demo/test_pattern_a2.py`: A2's defining behavior includes
Copilot Studio synthesis. Test it in Copilot Studio or benchmark the published
A2 agent through Direct Line.

**Copilot Studio prompt:** Use the
[A2 prompt contract](CopilotStudioIntegration.md#a2-prompt-contract), then try
`Compare the uniform and non-uniform dress code policies.` Confirm the activity
trace contains a Foundry IQ retrieval and the answer uses Policies 60010 and
60020.

## Pattern B: Foundry PromptAgent with required MCP retrieval

**Use when:** Foundry should own answer synthesis and every answer must retrieve
from the KB first.

**Setup and verification**

```bash
uv run python -m src.agents.create_foundry_agent --dry-run
uv run python -m src.agents.create_foundry_agent
uv run python -m src.agents.create_foundry_agent --verify-only
```

The provisioning sequence is:

```text
hr-policy-index -> hr-knowledge-source -> hr-knowledge-base
                -> hr-knowledge-mcp-connection -> HRPolicyAgent
```

`tool_choice="required"` forces `knowledge_base_retrieve` before synthesis.
Connect Copilot Studio to the external Foundry agent when Copilot Studio is the
front door; this direct external-agent connection requires a standard-harness
Copilot Studio agent. Pattern B can also be invoked directly for development.

**Files and why they matter**

| File | Role |
| --- | --- |
| `src/agents/create_foundry_agent.py` | Provisions the KB, MCP connection, and versioned PromptAgent definition. |
| `src/agents/hr_policy_agent.py` | Initializes and invokes `HRPolicyAgent` through the Responses API. |
| `src/backend/main.py` | Exposes `/api/chat` when using the backend/custom-connector route. |
| `copilot/openapi-v2.json` | OpenAPI contract for that backend route; not needed when Copilot Studio connects directly to the external agent. |
| `scripts/demo/test_pattern_b.py` | Live PromptAgent/MCP smoke test. |
| `src/benchmarking/adapters/agent.py` | Normalized Foundry-agent benchmark boundary. |
| `tests/test_foundry_agent_provisioning.py` | Protects the KB model endpoint and required-tool payload. |

**Smoke test**

```bash
uv run python -m scripts.demo.test_pattern_b \
  -q "Compare full-time and part-time PTO and cite both policies."
```

See [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md) for internals.
The exact server-side behavior and Copilot Studio instruction split is in the
[Pattern B prompt contract](CopilotStudioIntegration.md#pattern-b-prompt-contract).

## Pattern C: deterministic document locator

**Use when:** the user needs a trusted document URL rather than a synthesized
answer, or native citation cards do not satisfy the output contract.

**Setup**

1. Complete shared indexing.
2. Run or deploy the FastAPI backend.
3. Import `copilot/openapi-lookup-v2.json` into Copilot Studio.
4. Configure routing with [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md).

```bash
uv run python -m src.backend.main
uv run python -m scripts.demo.test_pattern_c \
  -q "Where is the Code of Ethics policy?"
```

**Files and why they matter**

| File | Role |
| --- | --- |
| `src/backend/main.py` | Implements `POST /api/lookup`. |
| `copilot/openapi-lookup-v2.json` | Defines the Copilot Studio REST tool. |
| `scripts/demo/test_pattern_c.py` | Exercises the deterministic lookup logic against live Search. |
| `src/benchmarking/adapters/pattern_c.py` | Normalizes locator output and exact-URL evidence. |

Pattern C is not an answer-quality replacement for A/A2/B. It is a different
contract: locate the authoritative document deterministically.

**Copilot Studio prompt:** Paste the complete
[Pattern C router instructions](CopilotStudioLookupRouting.md#pattern-c-router-instructions),
then try `Give me the link to the part-time PTO policy.` Expect the exact source
URL and filename, not a policy summary.

## Hosted Agent: Agent Framework in your container

**Use when:** you need custom authentication, middleware, sidecars, or ownership
of the request loop. Copilot Studio can still be the front door.

**Run locally or deploy**

```bash
uv run python -m scripts.demo.test_pattern_hosted

cd src/hosted_agent
uv run python server.py
# Deployment from the repository root uses azd deploy.
```

**Files and why they matter**

| File | Role |
| --- | --- |
| `src/agents/hr_policy_agent_af.py` | Agent Framework agent and `search_hr_policies` tool. |
| `src/hosted_agent/server.py` | Hosts the agent with the Foundry Responses protocol. |
| `src/hosted_agent/agent.yaml` | Declares hosted-agent resources, protocol, and environment. |
| `src/hosted_agent/Dockerfile` and `requirements.txt` | Build the deployable runtime. |
| `azure.yaml` | Declares the `azure.ai.agent` service for azd. |
| `src/benchmarking/adapters/agent.py` | Normalizes the hosted invocation boundary. |

The Hosted Agent supports direct Search and agentic context modes. See
[AgentArchitecturePaths.md](AgentArchitecturePaths.md) for the runtime tradeoff
and [Hosted prompt contract](CopilotStudioIntegration.md#hosted-prompt-contract)
for wiring and instruction ownership.

**Hosted prompt:** Do not paste a second system prompt into Copilot Studio. The
container loads `HR_POLICY_SYSTEM_PROMPT`; change it in
`src/agents/hr_policy_agent_af.py` and redeploy the container. Then try
`Which IT policies govern employee devices, acceptable use, and information
security?` and confirm a `search_hr_policies` call retrieves Policies 70070,
70010, and 70020 before synthesis.

## Smoke tests are not benchmarks

The files under `scripts/demo/` answer “does this path work?” They execute one
or a few live calls and print observed wall time. They do not provide controlled
sample counts, compatible manifests, confidence limits, load isolation, or cost
evidence. Do not quote their timing labels as benchmark findings.

| Layer | Purpose | Entry point |
| --- | --- | --- |
| Unit tests | Fast contract and regression checks | `uv run pytest -q` |
| Live smoke tests | Verify one configured path and inspect its answer | `uv run python -m scripts.demo.test_pattern_*` |
| Story demo | Walk A, B, C, Hosted decision branches; A2 remains a Copilot Studio path | `uv run python -m scripts.demo.demo_decision_tree` |
| Controlled benchmark | Versioned dataset + manifest + normalized report | `python -m src.benchmarking.cli ...` |
| Capacity/load evidence | Concurrent workload kept separate from controlled results | [BenchmarkLoadTesting.md](BenchmarkLoadTesting.md) |
| Production evidence | Search/Foundry/Application Insights/Azure Monitor telemetry | KQL under `experiments/kql/` |

## Run the current benchmark work

The benchmark asks a different question from the published article. The article
explains **which architecture exists and when to choose it**. The benchmark asks
**what comparable evidence supports that choice in this environment**.

### Offline contract smoke

This validates schemas and report generation only. It is not Azure performance
evidence.

```bash
python -m src.benchmarking.cli \
  --manifest experiments/manifests/synthetic-direct-search.json \
  --cases experiments/datasets/synthetic-migration-smoke.json \
  --fixture-responses experiments/datasets/synthetic-direct-search-responses.json \
  --output-dir experiments/reports/synthetic-direct-search
```

### End-to-end Copilot Studio comparison

Create five non-production Copilot Studio agents, each exposing exactly one
path: A, A2, B, C, or Hosted. Use the same instructions, selected Copilot model,
dataset, corpus/index fingerprints, and run conditions.

1. Use `scripts/generate_copilot_benchmark_manifests.py` to create one versioned
   manifest per exported agent.
2. Use `experiments/datasets/copilot-hr-policy-v1.json` as the common cases.
3. Publish each agent to the Mobile app channel and run the CLI with
   `--copilot-studio` plus that agent's schema and token endpoint.
4. Compare only compatible reports. Preserve missing telemetry as unavailable,
   never as zero.

The complete commands and publication checks are in
[CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md). The CLI directly
automates the repository Search boundary for Pattern A and the Direct Line
boundary for any configured pattern agent. Other direct adapters exist as
normalization components but are not all exposed as standalone CLI switches.

## Published article and benchmark evidence

### Published article: architecture decision model

[Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337)
defines the five patterns implemented here:

- one index, many front doors;
- classic versus agentic retrieval;
- answer synthesis versus deterministic document location;
- managed Foundry Agent Service versus a hosted Agent Framework runtime.

This repository is the article's executable companion. Pattern names in code,
docs, manifests, and reports must retain that meaning.

### Current benchmark work: reproducible evidence

`src/benchmarking/`, `experiments/`, and the benchmark documents add:

- versioned manifests and configuration fingerprints;
- normalized case and aggregate reports;
- deterministic citation, refusal, locator, and retrieval grading;
- explicit measurement boundaries for direct components and Copilot Studio;
- separate controlled, load, production-telemetry, and cost evidence;
- Pareto and SLO qualification without silently treating missing values as zero.

### Benchmark evidence gate

The [Copilot Studio benchmark workflow](CopilotStudioBenchmarking.md) requires
committed, compatible result artifacts before making comparative latency,
quality, reliability, or cost claims. Until those connected runs are complete,
timing values elsewhere in this repository are illustrative only.

## Where to go next

- Build one pattern: [patterns/README.md](patterns/README.md)
- Compare pattern concepts: [RetrievalPatterns.md](RetrievalPatterns.md)
- Configure five isolated pattern agents: [CopilotStudioTestingGuide.md](CopilotStudioTestingGuide.md)
- Understand ingestion: [DataPipelineAndTesting.md](DataPipelineAndTesting.md)
- Run the benchmark: [CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md)
- Run capacity tests separately: [BenchmarkLoadTesting.md](BenchmarkLoadTesting.md)
- Find every document by purpose: [docs/README.md](README.md)