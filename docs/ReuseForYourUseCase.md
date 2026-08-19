# Reuse This Benchmark for Your Own Use Case

This project is two things: a **domain-agnostic benchmark + decision system** (reusable
as-is) and a **thin HR-policy use case** layered on top. Swapping the use case is
mostly data and prompts — the engine, contracts, workbench, evaluation, Pareto/SLO,
and cost model do not change.

Estimated effort: **~80% is reusable unchanged.** A new RAG/agent use case is a
1–2 day adaptation, not a rewrite.

## What is reusable unchanged

| Area | Path | Reuse |
| --- | --- | --- |
| Benchmark contracts (manifest, case, aggregate) | `src/benchmarking/models.py` | As-is |
| Runner, adapters, aggregation, reporting | `src/benchmarking/` | As-is |
| Decision system (Pareto, SLO gates, comparison scope) | `src/benchmarking/` + API | As-is |
| Pattern adapters (direct search, KB retrieve, Foundry agent, hosted, Copilot Studio, Pattern C) | `src/benchmarking/adapters/` | As-is |
| Cost pricing (versioned token profiles) | `experiments/pricing/`, `src/benchmarking` | Add your model's profile |
| Evaluation (deterministic gates + judge attach) | `src/evaluation/`, `src/benchmarking/evaluation_attachment.py` | Reuse; edit graders |
| Observability / tracing | `src/observability/` | As-is |
| React workbench (Overview, Experiments, Compare, Pareto, Operations, Coverage, Glossary) | `src/frontend/` | As-is; edit copy |
| Infrastructure (Foundry + AI Search + Container Apps, Bicep/Terraform) | `infra/` | Reuse; rename resources |
| Hosted-agent packaging + retrieval modes | `src/hosted_agent/` | Reuse; swap prompt/index |

## What you must change (use-case surface)

1. **Corpus + index.** Replace `data/knowledge_base/` with your documents and re-run the
   indexing scripts (`scripts/index_knowledge_base_*.py`). Update the index field names in
   `src/config/search_config.json` (this repo uses `policy_number`, `policy`,
   `parent_title` — rename to your schema). Recompute the corpus/index fingerprints in
   manifests.
2. **Dataset + expected behaviors.** Replace the question sets and ground truth:
   - `eval/datasets/hr_qa_testset.csv` (curated Q/expected)
   - `experiments/datasets/*.json` (+ `-evaluation.json` specs)
   - `src/hosted_agent/.foundry/datasets/*.jsonl` (Foundry eval)
   Keep the same columns; only the content changes.
3. **Agent prompts.** Update the system prompts for your domain (they hardcode "HR policy"):
   - `_build_prompt_agent_definition()` in `src/agents/create_foundry_agent.py`
     — **the deployed Pattern B `HRPolicyAgent` prompt** (embeds
     `retrieval_instructions` / `answer_instructions` from
     `src/config/search_config.json`); verify in the Foundry portal under
     **Agents → HRPolicyAgent → Instructions**.
   - `HR_POLICY_INSTRUCTIONS` / `HR_POLICY_CONTEXT_INSTRUCTIONS` in
     `src/hosted_agent/server.py` — **the deployed Hosted `hr-policy-agent`
     container prompt**.
   - `HR_POLICY_SYSTEM_PROMPT` / `HR_POLICY_CONTEXT_SYSTEM_PROMPT` in
     `src/agents/hr_policy_agent_af.py` — the local benchmark Hosted agent.
   - `AGENT_INSTRUCTIONS` in `src/agents/hr_policy_agent.py` — the optional
     `/api/chat` Responses overlay only (not the deployed Pattern B agent).
4. **Citation format.** The citation parsers expect `[Policy NNNNN - Title]`. Change the
   regex in `src/agents/hr_policy_agent_af.py`, `src/benchmarking/adapters/foundry_hosted.py`,
   and the deterministic graders to your citation shape (e.g. `[Doc 12 - Title]`).
5. **Deterministic graders.** Edit the pass criteria in `src/evaluation/graders.py` and
   the security criterion in `evaluation_attachment.py` to match your domain's
   "correct answer" and safety rules.
6. **Copilot Studio agents (only if you use Patterns A/A2/B/C).** Rebuild your own
   published agents and set their schemas/token endpoints in `.env` (`COPILOT_STUDIO_*`).
   Not needed for Foundry-only patterns (B, Hosted).
7. **Branding + copy.** App name (`Pattern Lab`, `src/frontend/index.html`, the brand block
   in `App.tsx`), the Overview hero/lede, and any HR-specific glossary entries in
   `src/frontend/src/pages/GlossaryPage.tsx` (most glossary terms are benchmark-generic and
   stay).
8. **Model + pricing.** Set your model in `AZURE_AI_MODEL_DEPLOYMENT_NAME` /
   `src/config/model_policy.py`, and add a versioned pricing profile under
   `experiments/pricing/` for cost estimates.

## What stays conceptually identical

- The **five patterns** (A direct KB, A2 harness, B Foundry agent, C dual-tool, Hosted) are
  architecture choices, not HR-specific — they apply to any grounded-answer use case.
- The **evidence rules** (controlled vs load vs production; measured vs fixture vs
  unavailable), **comparison scope** (fails closed on mismatched dataset/index/model/mode/
  boundary), **SLO gates**, **Pareto**, and the **two cost lanes** (Foundry per-token USD vs
  Copilot Credits) are domain-agnostic.

## Suggested adaptation order

1. Fork, rename the app + resources, deploy `infra/` for a new environment.
2. Swap corpus → re-index → update `search_config.json` field names.
3. Swap datasets + expected behaviors + graders + citation regex.
4. Update the three prompt sets.
5. Add your model's pricing profile; run one fixture smoke, then one live component run.
6. (Optional) Build Copilot Studio agents for the front-door patterns.
7. Re-brand the workbench copy.

See also: [AgentArchitecturePaths.md](AgentArchitecturePaths.md) (pattern boundaries,
retrieval modes, eval lanes) and [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md)
(evidence rules and the decision surface).
