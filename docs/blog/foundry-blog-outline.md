# Blog Outline — Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ: Five Retrieval Patterns for an HR Knowledge Assistant

> **Target publication:** [Microsoft Foundry Blog (Microsoft Community Hub)](https://techcommunity.microsoft.com/category/azure-ai-foundry/blog/azure-ai-foundry-blog)
> **Status:** Draft outline for author review
> **Est. read time target:** 10–14 min (in line with recent technical posts on this blog)

---

## 0. Pre-submission metadata (fill in before drafting)

These map to the fields the Foundry Tech Community blog process requires. Confirm exact field names against **Foundry-TechCommunity-Blog-Process 5.28.26.docx** before submitting.

| Field | Value / Notes |
| --- | --- |
| **Working title** | See title options in §1. Keep under ~60 chars for SEO; no superlatives (see CELA §11). |
| **Category / board** | Microsoft Foundry Blog |
| **Suggested tags** | `Azure AI Foundry`, `Azure AI Search`, `Copilot Studio`, `AI Agents`, `Generative AI`, `RAG` |
| **Author byline + bio** | 2–3 sentence bio, role, link to profile |
| **Author headshot** | Square, per playbook spec |
| **Hero / featured image** | 1200×627 (verify current spec in playbook); include descriptive alt text |
| **CTA target** | Public GitHub repo + Microsoft Learn docs (no internal links) |
| **Reviewers** | Technical reviewer + CELA self-check completed (see §12 checklist) |
| **Read-time label** | Confirm the "X MIN READ" is auto-generated or manually set |

---

## 1. Title options (SEO-friendly, no red-flag superlatives)

- **A (recommended):** "Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ: Five Retrieval Patterns"
- **B:** "From Classic Search to Agentic Retrieval: Wiring Copilot Studio to Foundry IQ for an HR Knowledge Assistant"
- **C:** "Choosing a Retrieval Pattern for Copilot Studio: Azure AI Search, Foundry IQ, and Foundry Agent Service"

> Avoid "best," "most secure," "fastest," "guaranteed," "enterprise-grade" in the title and headings — these are CELA red-flag terms. Prefer descriptive, comparative-neutral phrasing.

---

## 2. Hook / Introduction (~150–250 words)

**Goal:** State the problem and who this is for in the first 2 sentences (matches the blog's house style — e.g., "Enterprise AI has a trust problem…").

- **The problem:** Employees ask HR questions in natural language ("How does PTO accrue?", "Where's the code of ethics policy?"), but the answers live in hundreds of policy documents. A single agent design rarely fits every query type.
- **The insight:** "Grounding" is not one decision — it's a spectrum from zero-code classic search to fully agentic retrieval. The right choice depends on *who orchestrates the search* and *how results reach the user*.
- **What the reader gets:** A decision framework plus five concrete, working retrieval patterns (A, A2, B, C, and a self-hosted runtime) built on Copilot Studio, Azure AI Search, and Foundry IQ — with the trade-offs that drive the choice.
- **Audience:** Developers and solution architects building knowledge agents on Microsoft Foundry.
- **Scope disclaimer (place near top or in a callout):** Reference the sample as a learning/reference implementation, not a production-ready deployment; point to the Well-Architected Framework for production hardening. (Pulls directly from the repo README disclaimer — keeps CELA happy on reliability/security claims.)

---

## 3. Scenario & sample overview (~150 words)

- Introduce the **"Ask HR"** sample: an assistant that answers employee questions from internal HR policy documents.
- The building blocks: **Azure AI Foundry**, **Azure AI Search**, **Microsoft Agent Framework (GA)**, **Copilot Studio**, plus **Foundry IQ** knowledge bases.
- One reusable asset underpins everything: the **`hr-knowledge-base`** (index + skillset + knowledge base). Emphasize that patterns layer on top **without re-indexing**.
- Link the public repo here (primary CTA anchor).

---

## 4. The core idea: a decision tree for retrieval (~200 words + diagram)

- **Insert Mermaid/exported decision-tree diagram** (from `docs/RetrievalPatterns.md`). Provide alt text describing the two decision axes.
- Walk the two questions that branch everything:
  1. **Do you need answer synthesis** (an LLM composing a response) or just to **locate a document**?
  2. If synthesis: **classic search vs agentic retrieval**, and **managed vs self-hosted runtime**?
- Define the two Microsoft terms clearly with Learn links:
  - **Classic search** — index-first, single hybrid query.
  - **Agentic retrieval** — the knowledge base plans sub-queries, retrieves in parallel, reranks, and merges results.

---

## 5. Pattern A — Direct Knowledge Base (classic search, zero agent code) (~200 words)

- **What it is:** Copilot Studio queries the Azure AI Search knowledge base directly via its built-in Knowledge action. No agent code in the answer path.
- **Why start here:** Lowest latency (~1–2 s), no LLM cost, fastest setup.
- **Native citations:** Copilot Studio surfaces a click-through citation card to the source document (via `blob_url` / `metadata_storage_path` mapping).
- **Limitation (be honest):** No forced answer synthesis — generative fallback can paraphrase; call this out as the reason to step up to B.
- **Provisioning snippet:** `python -m src.agents.create_foundry_agent --skip-agent`.

---

## 6. Pattern A2 — Copilot Studio (new experience) → Microsoft IQ → Foundry IQ (~250 words) — *the headline pattern*

- **What it is:** In the Copilot Studio **new agent experience** (preview), the agent connects **directly to a Foundry IQ knowledge base** via **Microsoft IQ** — **no Foundry prompt agent in the path**. This is **agentic retrieval**.
- **Why it matters (this is the "new and noteworthy" angle the blog favors):** agentic-retrieval quality with nothing extra to maintain; the KB is a centrally tuned, reusable asset — tune it in Foundry, not in Copilot Studio.
- **Wiring steps (numbered, with a screenshot):** Build → Microsoft IQ → Foundry IQ → Create new connection (Microsoft Entra ID Integrated) → select `hr-knowledge-base` → Add to agent.
- **Security framing (CELA-safe wording):** With Entra ID Integrated auth, the signed-in user's identity flows through, so results are **ACL-trimmed per user**. Note the KB inherits enterprise-readiness controls (CMK, network isolation, Entra ID) — describe as *available controls*, **not** as an absolute "fully secure/compliant" guarantee.
- **When A2 vs A vs B:** A = classic search over an index; A2 = agentic retrieval over a KB; B = KB wrapped in a Foundry prompt agent with forced grounding.
- Link: Connect to Foundry IQ from an agent (preview) on Microsoft Learn.

---

## 7. Pattern B — Foundry Agent Service + MCPTool (force-grounded synthesis) (~200 words)

- **What it is:** A `PromptAgentDefinition` published to the Foundry project; its only tool is an `MCPTool` on the KB endpoint with `tool_choice="required"` — the model is *forced* to ground every answer in retrieved chunks.
- **Why:** Answer synthesis with strict grounding, single SDK call; managed runtime.
- **Code anchor:** `src/agents/hr_policy_agent.py`; invoke via `openai.responses.create(extra_body={"agent_reference": {...}})`.
- **Latency honesty:** ~10–14 s — the cost of synthesis.
- Include a short, real code snippet (agent definition + invocation).

---

## 8. Pattern C — Dual-Tool Routing (deterministic document locator) (~180 words)

- **What it is:** Copilot Studio routes per turn — "Where is the PTO policy?" → `POST /api/lookup` (no LLM, ~1–2 s); "How much PTO do I accrue?" → Pattern A/B.
- **When to add it (set expectations):** Only when native citations aren't enough — i.e., you need sub-second latency, the URL in the answer body verbatim, or deterministic/auditable output.
- **Anchors:** `src/backend/main.py:/api/lookup`, `copilot/openapi-lookup-v2.json`.

---

## 9. Hosted Agent — Microsoft Agent Framework runtime (self-hosted, classic + agentic) (~200 words)

- **What it is:** A container running `Agent` (Microsoft Agent Framework, GA) with `FoundryChatClient`. Supports both classic and agentic RAG via `RETRIEVAL_MODE` (`tool`, `context-semantic`, `context-agentic`).
- **Why:** Full runtime control (custom auth, side-car services) while keeping parity with the managed Foundry path.
- **Key nuance:** the `context-*` modes use Agent Framework's out-of-the-box RAG context provider — retrieval runs automatically before each turn.
- **Anchors:** `src/hosted_agent/server.py`, `agent.yaml`, `Dockerfile`.
- Note the front door is still Copilot Studio for both B and Hosted.

---

## 10. Side-by-side comparison + how to choose (~150 words + table)

- **Insert the pattern comparison table** (orchestrator, LLM call, search type, latency, citations, setup cost, best-for). Adapt from `docs/RetrievalPatterns.md`.
- One-paragraph guidance: start at A, step to A2 for agentic retrieval without maintaining an agent, B for forced synthesis in Foundry, C for deterministic locators, Hosted for runtime control.
- Frame trade-offs neutrally (latency vs synthesis vs control) — avoid "best" language.

---

## 11. Try it yourself / Call to action (~120 words)

- Link the **public GitHub repo** and the **Walkthrough** (Steps 1–3 for Pattern A).
- Provide the fastest path: provision the KB, connect Copilot Studio, ask a question — in minutes.
- Link **Microsoft Learn**: Foundry IQ, agentic retrieval, prompt agents, Agent Framework hosting.
- Invite comments/feedback (drives engagement metrics the playbook cares about).
- Reiterate the dev/reference-only disclaimer + WAF link.

---

## 12. CELA / submission compliance checklist (do before submitting)

Reconcile every item against the source docs; this is a working checklist, not a substitute for them.

**Red-flag terms (from CELA "Red flag terms in advertising and marketing"):**
- [ ] No absolute superlatives: "best," "fastest," "most secure," "#1," "leading."
- [ ] No guarantees: "guaranteed," "ensures," "100%," "never fails," "always."
- [ ] No absolute security/compliance claims: say "helps protect," "supports," "designed to" — not "fully secure," "unhackable," "bank-grade," "military-grade," "compliant" (unqualified).
- [ ] No unqualified performance/cost claims (quantify latency as *observed in this sample*, not a promise).
- [ ] No competitor disparagement or unverifiable comparisons.
- [ ] Replace "seamless / effortless / frictionless" with concrete, verifiable descriptions.

**CELA self-check tool ("Using the CELA Self-Check Tool for Blog Reviews"):**
- [ ] Run the self-check tool on the full draft; resolve every flag.
- [ ] Confirm all product names use current, approved branding (Microsoft Foundry, Azure AI Foundry, Azure AI Search, Copilot Studio, Microsoft Agent Framework).
- [ ] Mark preview features explicitly as "(preview)" — e.g., Copilot Studio new agent experience, Foundry IQ connection.

**Foundry blog process ("Foundry-TechCommunity-Blog-Process"):**
- [ ] Title, tags, category set; read-time appropriate.
- [ ] Author bio + headshot supplied.
- [ ] Hero image at required dimensions; **alt text on every image/diagram** (accessibility).
- [ ] All links are public (Microsoft Learn, public GitHub) — **no internal SharePoint / aka.ms-internal links**.
- [ ] No confidential, unreleased, or internal-only information.
- [ ] Code snippets tested and minimal; secrets/endpoints redacted.
- [ ] Disclaimer that the sample is for development/learning, not production.
- [ ] Technical review sign-off obtained.

**Playbook ("Azure Tech Community Playbook") engagement items:**
- [ ] Clear CTA + repo link.
- [ ] Social share plan / cross-post (LinkedIn) prepared.
- [ ] Tags chosen to match high-traffic blog tags (Azure AI Search, AI Agents, Generative AI).

---

## 13. Assets to prepare

- [ ] Hero image (1200×627) with alt text.
- [ ] Decision-tree diagram (export the Mermaid from `docs/RetrievalPatterns.md` to PNG/SVG).
- [ ] Screenshot: Copilot Studio Foundry IQ connection wiring (Pattern A2).
- [ ] Screenshot: a grounded answer with a citation card.
- [ ] 2–3 tested code snippets (Pattern B agent definition + invocation; Pattern C lookup call).
- [ ] Comparison table (from §10).

---

## 14. Source material in this repo (for drafting)

- Retrieval patterns & comparison table: `docs/RetrievalPatterns.md`
- Copilot Studio wiring (incl. Pattern A2): `docs/CopilotStudioIntegration.md`
- Pattern C routing: `docs/CopilotStudioLookupRouting.md`, `docs/CopilotStudioHybridExample.md`
- Pattern B internals: `docs/FoundryAgentArchitecture.md`
- Setup steps for CTA: `docs/Walkthrough.md`
- Repo overview + disclaimer language: `README.md`
