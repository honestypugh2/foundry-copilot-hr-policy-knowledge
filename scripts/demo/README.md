# Pattern Test Scripts + Decision-Tree Demo

Live, runnable scripts that exercise each retrieval pattern in this
repo against the configured Azure resources, plus a storytelling demo
that walks the decision tree end-to-end.

These are **integration scripts**, not unit tests. They hit the real
`hr-policy-index`, real Azure OpenAI, and (for Pattern B / Hosted) the
real Foundry project. For the mocked unit tests, see `tests/`.

> **TL;DR.** Run `python -m scripts.demo.demo_decision_tree` for the full
> story. Run `python -m scripts.demo.test_pattern_<a|b|c|hosted>` for a
> single pattern. Both honor `--question` / `-q` to swap the prompt.

---

## Files

| Script | Pattern | Lab origin | Latency | Needs Foundry agent? |
| ------ | ------- | ---------- | ------- | -------------------- |
| [`test_pattern_a.py`](test_pattern_a.py) | **A** — Direct KB (★ default) | Lab 1.4, Lab 2.1 Option 1 | ~1–2 s | No |
| [`test_pattern_b.py`](test_pattern_b.py) | **B** — Foundry Agent + MCPTool | Lab 2.4 (Foundry side) | ~10–14 s | **Yes** — run `create_foundry_agent` first |
| [`test_pattern_c.py`](test_pattern_c.py) | **C** — Dual-Tool Routing | Lab 2.1 Options 2 & 3, Lab 2.4 (quick path) | ~1–2 s | No |
| [`test_pattern_hosted.py`](test_pattern_hosted.py) | Hosted Agent (Agent Framework GA hosting) | — | ~10–14 s | No (uses `FoundryChatClient` directly) |
| [`demo_decision_tree.py`](demo_decision_tree.py) | All of the above | All four labs | sum of the above | Optional (auto-skips with a warning) |
| [`_common.py`](_common.py) | shared helpers | — | — | — |

---

## Prerequisites

All scripts read environment from `.env` via `python-dotenv`, the same
file the FastAPI backend uses.

| Variable | Used by | Notes |
| -------- | ------- | ----- |
| `AZURE_SEARCH_ENDPOINT` | A, B, C, Hosted | Required everywhere |
| `AZURE_SEARCH_API_KEY` | A, C, Hosted | Optional — `DefaultAzureCredential` is used as fallback |
| `AZURE_SEARCH_INDEX_NAME` | All | Defaults to `hr-policy-index` |
| `AZURE_AI_PROJECT_ENDPOINT` | B, Hosted | Foundry project endpoint |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | B, Hosted | Defaults to `gpt-4.1` |

The `hr-policy-index` must already be populated. From the repo root:

```bash
uv run python scripts/index_knowledge_base_integrated_vectorization.py
```

For **Pattern B**, you also need to provision the PromptAgent once:

```bash
uv run python -m src.agents.create_foundry_agent
```

---

## Quick start

```bash
# Activate the project venv first
source .venv/bin/activate

# Run a single pattern with the default question
python -m scripts.demo.test_pattern_a
python -m scripts.demo.test_pattern_c

# Pattern B (requires Foundry agent provisioned)
python -m scripts.demo.test_pattern_b

# Hosted agent (Agent Framework runtime)
python -m scripts.demo.test_pattern_hosted

# Override the question
python -m scripts.demo.test_pattern_a -q "What is the dress code policy?"
python -m scripts.demo.test_pattern_c -q "Where can I download the Code of Ethics?"

# Full storytelling demo — walks every act of the decision tree
python -m scripts.demo.demo_decision_tree

# Demo with selected acts skipped
python -m scripts.demo.demo_decision_tree --skip-b --skip-hosted

# Demo with custom questions
python -m scripts.demo.demo_decision_tree \
  --content "How much PTO do part-time employees accrue?" \
  --locator "Give me the link to the PTO policy"
```

The demo ends with a side-by-side latency table so you can see the
~1–2 s (A, C) vs ~10–14 s (B, Hosted) gap in your own environment.

---

## What each script proves

### `test_pattern_a.py`
Replicates `src/backend/main.py:_pattern_a_answer` exactly:
1. Glossary expansion (`expand_query_with_glossary`).
2. Hybrid search via `IntegratedVectorizationSearchService.search()`.
3. Deterministic concatenation of the top-3 hits with policy citations.

This is **byte-for-byte the same retrieval shape** that Copilot
Studio's native "Add knowledge → Azure AI Search" connector runs
against `hr-policy-index`, which is why Pattern A is the default.

### `test_pattern_b.py`
1. Constructs `HRPolicyAgent` (Foundry path).
2. Calls `initialize()` to ensure the PromptAgent exists.
3. Invokes `answer_question_async()` which calls the Responses API with
   `agent_reference={"name":"HRPolicyAgent"}` — `MCPTool` runs
   server-side with `tool_choice="required"`.

If the Foundry client is unavailable (e.g. agent not provisioned), the
agent falls back to local search and prints a warning — the script
still exits 0 so it's safe in CI.

### `test_pattern_c.py`
Replicates `src/backend/main.py:/api/lookup`:
1. Glossary expansion (same as Pattern A).
2. Hybrid search over the same index, but projected into the
   metadata-only shape (`policy_number`, `parent_title`,
   `metadata_storage_name`, `metadata_storage_path`, `blob_url`,
   `score`).
3. Prints the routing levers used by the Copilot Studio side
   ([CopilotStudioLookupRouting.md](../../docs/CopilotStudioLookupRouting.md)).

### `test_pattern_hosted.py`
Runs `hr_policy_agent_af.HRPolicyAgent` end-to-end: Agent Framework
`Agent` + `FoundryChatClient` + `@tool search_hr_policies`. This is
the same agent the self-hosted container in `src/hosted_agent/`
serves; the script just exercises the class directly so you don't
have to build/deploy a container.

### `demo_decision_tree.py`
Four-act storytelling walk-through:
- **Act 1** — Pattern A (Lab 1.4)
- **Act 2** — Pattern B (Lab 2.4 Foundry side)
- **Act 3** — Native citations alternative → Pattern C (Lab 2.1 Options 2 & 3)
- **Act 4** — Hosted Agent (Agent Framework GA hosting)

Each act prints the decision-tree branch being taken, the lab it
maps to, and the relevant code path. The final "curtain call"
prints a comparison table of pattern × result × latency × lab
origin.

---

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | All requested patterns ran successfully |
| `1`  | One or more requested patterns failed |
| `2`  | Required env vars missing (preflight failed) |
| `130` | Demo aborted (Ctrl+C) |

---

## See also

- [docs/RetrievalPatterns.md](../../docs/RetrievalPatterns.md) — full pattern detail
- [docs/LabCoverage.md](../../docs/LabCoverage.md) — cross-walk to Azure/Copilot-Studio-and-Azure labs
- [docs/CopilotStudioLookupRouting.md](../../docs/CopilotStudioLookupRouting.md) — Pattern C vs native citations
- [tests/](../../tests/) — unit tests (mocked, fast, CI-friendly)
