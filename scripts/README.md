# `scripts/` — Indexing & Utility Scripts

This directory holds the scripts that **populate the Azure AI Search index**
(`hr-policy-index`) plus supporting utilities. Every retrieval pattern in this
repo — **A, A2, B, C, and the Hosted Agent** — ultimately reads from that same
index (directly, or through the `hr-knowledge-base` built on top of it), so
getting the index populated is step one for any demo.

> **Two "pattern" vocabularies — don't confuse them.**
> - **Retrieval patterns** (A / A2 / B / C / Hosted) describe *how Copilot
>   Studio reaches an answer* — see [../docs/RetrievalPatterns.md](../docs/RetrievalPatterns.md).
> - **Data-pipeline patterns** ("Pattern 1 Option 1 / Option 2") describe *how
>   documents get into the index* — see [../docs/DataPipelineAndTesting.md](../docs/DataPipelineAndTesting.md).
>   The indexing scripts below are the data-pipeline options. All retrieval
>   patterns consume whichever index you build.

---

## Indexing scripts at a glance

| Script | Status | Data-pipeline | Chunking | Embeddings | When to use |
| ------ | ------ | ------------- | -------- | ---------- | ----------- |
| [`index_knowledge_base_integrated_vectorization.py`](index_knowledge_base_integrated_vectorization.py) | ✅ **Current** | Pattern 1 **Option 2** — indexer/skillset (server-side) | Document Intelligence Layout skill (structure-aware) | `AzureOpenAIEmbeddingSkill` (server-side) | **Production / default.** Auto-reprocesses on blob changes. The path wired into the Walkthrough, testing guide, and demo. |
| [`index_knowledge_base_docintel_chunking.py`](index_knowledge_base_docintel_chunking.py) | ✅ **Current** | Pattern 1 **Option 1** — push (client-side) | Document Intelligence + fixed-size (2000/200) | `text-embedding-3-small` (client-side) | **Dev / test.** Full control of preprocessing; no indexer to manage. |

Both target the **same index** (`hr-policy-index`) and the **same shared
schema/synonym map/semantic config** in [`../src/config/search_config.json`](../src/config/search_config.json),
so search behavior is consistent regardless of which you run. **Pick one** —
you do not run both.

### Which one do I need?

The two scripts are the two supported preprocessing options (server-side vs
client-side) — keep both:

- **`index_knowledge_base_integrated_vectorization.py`** for production/default
  (indexer auto-reprocesses blob changes).
- **`index_knowledge_base_docintel_chunking.py`** for dev/test (full client-side
  control, no indexer to manage).

> Two earlier scripts (`index_knowledge_base.py`, `index_knowledge_base_chunking.py`)
> were removed as deprecated — they lacked structure-aware chunking and the
> shared synonym map / semantic config. Use one of the two above instead.

---

## How indexing maps to the retrieval patterns

One indexing run produces the artifacts each pattern consumes:

| Retrieval pattern | What it queries | Produced by |
| ----------------- | --------------- | ----------- |
| **A** — Copilot Studio → Azure AI Search index | `hr-policy-index` (classic search) | Either current indexing script |
| **A2** — Copilot Studio (new) → Foundry IQ | `hr-knowledge-base` (agentic retrieval) | Indexing script **+** `python -m src.agents.create_foundry_agent` (builds the KB on the index/blob) |
| **B** — Foundry prompt agent + MCPTool | `hr-knowledge-base` via MCP | Indexing script **+** `python -m src.agents.create_foundry_agent` |
| **C** — Dual-tool `/api/lookup` | `hr-policy-index` (metadata fields) | Either current indexing script |
| **Hosted Agent** — `search_hr_policies` tool | `hr-policy-index` (hybrid + semantic) | Either current indexing script |

**Takeaways**
- **Patterns A / C / Hosted** need only a populated `hr-policy-index` → run one
  current indexing script.
- **Patterns A2 / B** additionally need the **knowledge base** → run one indexing
  script, then `python -m src.agents.create_foundry_agent` (in `../src/agents/`,
  not this folder).

---

## Recommended flow

```bash
# 1. (Integrated vectorization only) uploads happen inside the script, but you
#    can pre-stage blobs with the helper below if preferred.
# 2. Populate the index — pick ONE:
uv run python scripts/index_knowledge_base_integrated_vectorization.py   # production/default
# — or —
uv run python scripts/index_knowledge_base_docintel_chunking.py          # dev/test

# 3. Only for Patterns A2 / B — build the Foundry IQ knowledge base:
uv run python -m src.agents.create_foundry_agent
```

Useful flags: `--local-only` (skip Azure Document Intelligence),
`--data-dir data/knowledge_base_lab` (index the lab corpus),
`--upload-only` / `--create-pipeline-only` (integrated vectorization stages).

---

## Supporting scripts

| Script | Purpose |
| ------ | ------- |
| [`upload_to_blob.py`](upload_to_blob.py) | Upload the `data/knowledge_base/ASK HR Knowledge/` files to the `ask-hr-knowledge` blob container (flat layout the integrated-vectorization indexer expects). |
| [`generate_architecture_diagram.py`](generate_architecture_diagram.py) | Render the architecture diagram(s) used in the docs. |
| [`setup.sh`](setup.sh) | Convenience environment bootstrap (dependencies + first-run hints). |
| [`demo/`](demo/) | Per-pattern local walkthroughs and smoke tests — see [`demo/README.md`](demo/README.md). |

---

## Related docs

- [../docs/DataPipelineAndTesting.md](../docs/DataPipelineAndTesting.md) — full pipeline internals (Option 1 vs Option 2)
- [../docs/RetrievalPatterns.md](../docs/RetrievalPatterns.md) — the retrieval patterns (A / A2 / B / C / Hosted)
- [../docs/Walkthrough.md](../docs/Walkthrough.md) — linear setup walkthrough
- [../README.md](../README.md) — top-level overview
