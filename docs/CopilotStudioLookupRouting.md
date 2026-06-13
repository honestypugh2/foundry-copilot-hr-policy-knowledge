# Copilot Studio Routing — Dual-Tool Setup (Pattern C)

This guide wires the HR policy agent in Copilot Studio so it routes by
itself between **content questions** and **document-location
questions**. The location path drops Foundry entirely — the routing
decision lives in Copilot Studio (agent instructions + tool
descriptions). There is no server-side orchestrator picking the path;
Copilot Studio's planner does it.

The Custom Lookup Tool itself — its name, description, and parameter
schema — mirrors the canonical `file_metadata_lookup` tool definition
from
[honestypugh2/foundry-copilot-search-validate](https://github.com/honestypugh2/foundry-copilot-search-validate/blob/main/src/agents/orchestrator_pattern_b.py).
That repo proves out the same tool inside a Foundry agent (Pattern B);
this repo exposes it as a REST tool to Copilot Studio. Same description
text on both sides → same routing behavior.

| Destination                                     | When                                                                                        | Latency                            | How it's wired                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------- |
| **Azure AI Search knowledge source** (Pattern A) | Content questions — what a policy says, eligibility, amounts, deadlines, process            | ~10–14 s (RAG + model synthesis)  | Knowledge source on the agent (or `askHRPolicy` REST tool) |
| **`lookupHRPolicyDocument` REST tool** (Pattern C) | Location questions — where a document is stored, file path, blob URL, link, filename       | ~1–2 s (single hybrid search)     | Custom REST tool from `copilot/openapi-lookup-v2.json`     |

> **Backend pattern is independent.** This guide assumes Pattern A
> (knowledge source) for content. If you prefer Pattern B (Foundry
> Agent Service), import `copilot/openapi-v2.json` as the content tool
> instead and keep everything else identical.

---

## 1. Add the lookup tool

1. In Copilot Studio open your agent → **Tools** → **+ Add a tool** →
   **New tool** → **REST API**.
2. Upload / paste [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json)
   (Swagger 2.0 — do not upload OpenAPI v3 YAML; the v3 → v2
   auto-translate can drop the body schema and auth).
3. **Authentication: API key.**
   - **Parameter name:** `code`
   - **Location:** `Query` ⚠️ change from the default `Header` —
     `Header` returns 401 against an Azure Functions function key.
   - **Value:** the function key —
     ```bash
     az functionapp keys list \
       -g <your-rg> -n <your-func-app> \
       --query "functionKeys.default" -o tsv
     ```
4. **Save.** Confirm the operation `lookupHRPolicyDocument` appears.

Keep the existing Azure AI Search knowledge source (Pattern A) on the
agent for content. If you don't have one yet, follow Path 1 of
[CopilotStudioIntegration.md](CopilotStudioIntegration.md) first.

---

## 2. Agent instructions (Lever 1 — the router)

Paste into the agent's **Instructions**. This is what makes Copilot
Studio pick the right path.

```
You are an HR policy assistant. Decide how to answer each question:

1. LOCATION questions — when the user asks WHERE a document is, or asks for a
   file path, storage path, blob URL, link, download link, or filename
   (e.g. "Where is the PTO policy stored?", "What's the file path for the
   Holiday Pay policy?", "Give me the link to the Code of Ethics document"):
   → Call the lookupHRPolicyDocument tool. Return the blob_url / file path and
     the filename exactly as the tool provides them. Do not summarize content.

2. CONTENT questions — when the user asks what a policy SAYS, how it works,
   eligibility, amounts, deadlines, or process (e.g. "How much PTO do I accrue?",
   "Who is eligible for holiday pay?"):
   → Answer from the HR policy knowledge source with citations. Do NOT call the
     lookupHRPolicyDocument tool.

3. If a question asks for BOTH the content and where to find it, answer the
   content from the knowledge source first, then call lookupHRPolicyDocument to
   append the document link.

Never invent file paths, URLs, or policy numbers. If the lookup tool returns
found = false, say you couldn't locate that document and ask the user to
clarify the policy name or number.
```

---

## 3. Tool description (Lever 2 — reinforce the boundary)

The `description` fields in `copilot/openapi-lookup-v2.json` are the
second routing lever. They mirror the reference repo's canonical
`file_metadata_lookup` tool definition verbatim:

> **Look up the storage location, file path, blob URL, and filename for
> a document in the HR policy knowledge base. Use this tool when the
> user asks WHERE a document is located, asks for a file path, URL,
> link, blob storage path, or document location. This performs a direct
> index search for metadata fields only — it does NOT use the
> knowledge base. Do NOT use this for content/policy questions.**

The input parameter `message` carries the same intent as the
reference's `query`:

> **The search query to find the document. Include policy number
> and/or document title.**

### What counts as a "location" query?

The reference repo's `_classify_query` regex is the explicit list of
triggers — use it as the test set when you tune the agent
instructions:

- `where is`, `where are`, `located`, `stored`
- `file path`, `storage path`, `metadata.storage.path`
- `blob url`, `blob path`, `blob location`
- `give me the link`, `download link`, `document location`

If you maintain a content tool (`askHRPolicy` from
[`copilot/openapi-v2.json`](../copilot/openapi-v2.json)) instead of a
knowledge source, keep its description in the **mirror-image** form:
**"Use for what a policy says… do NOT use for where a document is
stored."** Clear, non-overlapping descriptions are the strongest
signal the planner has.

---

## 4. Verify routing (Test pane)

| # | Utterance                                                         | Expected tool                  | Notes                                                          |
| - | ----------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------- |
| 1 | Where is the PTO policy stored?                                   | `lookupHRPolicyDocument`       | `blob_url` + filename, ~1–2 s, no prose summary                |
| 2 | What's the file path for the Holiday Pay policy?                  | `lookupHRPolicyDocument`       | `metadata_storage_path` returned verbatim                      |
| 3 | Give me the link to the Code of Ethics document                   | `lookupHRPolicyDocument`       | `blob_url` for policy 31000                                    |
| 4 | How much PTO do I accrue per year?                                | Knowledge source / `askHRPolicy` | Cited answer from PTO policy 51350, **no** lookup tool call    |
| 5 | Who is eligible for holiday pay?                                  | Knowledge source / `askHRPolicy` | Cited answer, no lookup tool call                              |
| 6 | Tell me about the Code of Ethics and where I can find it          | Knowledge source **then** tool | Content answer + appended link                                 |
| 7 | Where can I download the Blood Borne Pathogens intro?             | `lookupHRPolicyDocument`       | `blob_url` for policy 101100                                   |

If a content question (4 / 5) wrongly calls the lookup tool, **tighten
instruction rule #2** and re-confirm the tool's operation description
hasn't been edited to sound generic.

---

## 5. Why this is fast

`POST /api/lookup` runs one hybrid search and returns metadata fields
only — no Foundry agent, no MCP, no LLM synthesis. That's the ~1–2 s
vs ~10–14 s difference. Content questions still go through the
knowledge source's RAG + synthesis, which is where the latency lives.

---

## See Also

- [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md) — the
  full click-by-click build (combines glossary + lookup + content).
- [`copilot/openapi-lookup-v2.json`](../copilot/openapi-lookup-v2.json) — tool spec.
- [`src/backend/main.py`](../src/backend/main.py) — `POST /api/lookup` implementation.
- [Reference: `orchestrator_pattern_b.py`](https://github.com/honestypugh2/foundry-copilot-search-validate/blob/main/src/agents/orchestrator_pattern_b.py)
  — canonical `file_metadata_lookup` tool definition + classifier regex.
- [Extend your agent with tools from a REST API (preview)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api)
