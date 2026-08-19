import { useMemo, useState } from "react";
import { BookOpen, Search } from "lucide-react";

type Term = {
  term: string;
  group: "Decision" | "Latency" | "Quality" | "Evidence" | "Cost" | "Retrieval";
  short: string;
  detail: string;
};

const TERMS: Term[] = [
  {
    term: "Pareto frontier",
    group: "Decision",
    short: "The set of options that are not beaten on every metric at once.",
    detail:
      "A run is on the Pareto frontier if no other comparable run is better on all gates simultaneously — you cannot improve its quality without giving up latency, cost, or reliability. It shortlists the non-dominated choices so you compare real trade-offs instead of one number.",
  },
  {
    term: "SLO gate",
    group: "Decision",
    short: "Project acceptance thresholds a run must pass to qualify for release.",
    detail:
      "Service-level objectives for this project (not Microsoft guarantees): deterministic quality ≥ 85%, Copilot Studio client p95 ≤ 30 s, success ≥ 99%, security = 100%, estimated variable cost ≤ $0.05/request. A run that fails any gate is not release-qualified.",
  },
  {
    term: "Comparison scope (fails closed)",
    group: "Decision",
    short: "The app refuses to rank runs that aren't truly comparable.",
    detail:
      "Two runs are only comparable when their dataset, corpus, index, model, retrieval mode, execution boundary, and git commit all match. Two runs from different commits — even on the same dataset — fail closed with an amber banner and are shown as directional context only, never a ranking. Compare's suggested candidates only list runs that share the exact scope, so they always produce a green banner.",
  },
  {
    term: "Release-ready",
    group: "Decision",
    short: "Passed every SLO plus the evidence-quality gates needed to publish a result.",
    detail:
      "A run is release-ready when it clears all SLO gates AND its evidence is trustworthy enough to publish: a clean git commit (no dirty worktree), real (non-synthetic) Copilot Studio front-door measurement, category-level deterministic quality, rate confidence intervals, and explicit outcome counts. Shown as the ‘Release-ready’ column on Pareto / SLO. (The underlying JSON field is named publication_ready.)",
  },
  {
    term: "Measurement boundary",
    group: "Decision",
    short: "What each measurement actually covers, end to end.",
    detail:
      "Examples: copilot_studio_direct_line (Copilot orchestration + retrieval + synthesis), foundry_hosted_agent (deployed managed runtime + network), agent_framework_local (in-process SDK). Numbers from different boundaries are not directly comparable.",
  },
  {
    term: "p50 / p95 / p99 latency",
    group: "Latency",
    short: "Percentiles of response time — not the average.",
    detail:
      "p50 is the median: half of requests were faster. p95 means 95% finished at or below that time and the slowest 5% took longer — the primary tail-latency signal. p99 exposes the extreme tail and is sensitive to a single slow request in small samples.",
  },
  {
    term: "Warm / cold",
    group: "Latency",
    short: "First call vs. subsequent calls.",
    detail:
      "Cold = the first invocation, which includes startup/initialization. Warm = later invocations. They are reported separately so startup time is never blended into steady-state latency.",
  },
  {
    term: "Deterministic quality",
    group: "Quality",
    short: "Rule-based pass/fail — the authoritative quality gate.",
    detail:
      "Objective checks such as 'cited the correct policy number' and 'grounded in retrieved content'. Unlike a model judge, it is reproducible, so it is used as the release gate. Reported as passed / total (e.g. 6/7 = 85.7%).",
  },
  {
    term: "Security pass rate",
    group: "Quality",
    short: "Share of adversarial probes the agent resisted.",
    detail:
      "Deterministic prompt-injection and secret-disclosure checks. The agent passes when it does not follow the injected instruction and does not disclose secrets/system prompts. 100% is required for release; any failure blocks it.",
  },
  {
    term: "Judge scores (supplemental)",
    group: "Quality",
    short: "LLM-graded relevance / intent — context, not a gate.",
    detail:
      "A held-out judge model scores relevance and intent-resolution (e.g. 4.86/5). These are supplemental signals; the deterministic gates remain the authority. The judge model is held constant across all patterns so scores stay comparable.",
  },
  {
    term: "answer_model",
    group: "Quality",
    short: "The effective answer model — pinnable vs. platform-managed.",
    detail:
      "gpt-5-mini where we control it (Foundry patterns), or a harness:model marker for Copilot Studio: microsoft_managed_standard_harness:claude-sonnet-4.6 (A, B, C, Hosted) and github_copilot_harness:claude-sonnet-4.6 (A2). The Copilot Studio model is selectable and recorded but bills in Copilot Credits, not tokens, so it never joins the Foundry per-token axis. Cross-platform quality is confounded by model, so compare within a platform first.",
  },
  {
    term: "Evidence states",
    group: "Evidence",
    short: "measured · fixture-only · run-required · unavailable.",
    detail:
      "measured = a committed real run with manifest and sample count. fixture-only = synthetic contract check, never Azure performance evidence. run-required = no comparable run exists yet. unavailable = the provider did not expose the metric (recorded as null with a reason, never zero).",
  },
  {
    term: "Wilson confidence interval",
    group: "Evidence",
    short: "Honest uncertainty band for a rate on small samples.",
    detail:
      "With only 35 samples, an observed 100% success rate still has a 95% Wilson lower bound near 90%. The interval keeps small-sample reliability claims honest instead of overstating a point estimate.",
  },
  {
    term: "Provenance",
    group: "Evidence",
    short: "The run's identity: commit, dataset, fingerprints, boundary, model.",
    detail:
      "Every report records git commit, dataset version, corpus/index fingerprint, measurement boundary, answer_model, and evaluation relationship so a result can be reproduced and trusted.",
  },
  {
    term: "Dirty worktree",
    group: "Evidence",
    short: "The run executed with uncommitted code changes — not reproducible.",
    detail:
      "When a benchmark runs while the git working tree has uncommitted edits, the exact code that produced the result cannot be recovered from a commit hash. That makes the run non-reproducible, so it is blocked from being release-ready even if every SLO passes. Re-run from a clean, committed state to clear it.",
  },
  {
    term: "Variable model cost",
    group: "Cost",
    short: "Per-token USD estimate for Foundry patterns.",
    detail:
      "Estimated from service-reported token usage × a versioned pricing profile (e.g. gpt-5-mini). Excludes shared Search capacity, hosting, and evaluator usage. Azure Cost Management remains authoritative for billed cost.",
  },
  {
    term: "Copilot Studio credits",
    group: "Cost",
    short: "Copilot Credits billing for Copilot Studio patterns — a different unit.",
    detail:
      "Copilot Studio bills in Copilot Credits, the common currency across Copilot Studio capabilities, rated per agent activity (Classic answer, Generative answer, Agent action). Billed consumption is reported in the Power Platform admin center under Licensing → Copilot Studio. It is Microsoft-managed and cannot be converted to per-token USD, so it is tracked as a separate cost lane.",
  },
  {
    term: "Retrieval modes",
    group: "Retrieval",
    short: "tool · context-semantic · context-agentic.",
    detail:
      "tool = the agent explicitly calls a classic search tool. context-semantic = a context provider injects classic hybrid-search results before each turn. context-agentic = agentic Knowledge Base retrieval that plans sub-queries and merges results before answering.",
  },
  {
    term: "Agentic retrieval phases",
    group: "Retrieval",
    short: "The query-planning trace behind agentic retrieval.",
    detail:
      "modelQueryPlanning → several searchIndex sub-queries → agenticReasoning. The workbench surfaces these phases (records, elapsed, reasoning tokens) so agentic retrieval is a white box, not a black box.",
  },
];

const GROUPS = ["Decision", "Latency", "Quality", "Evidence", "Cost", "Retrieval"] as const;

export default function GlossaryPage() {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState<string>("All");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return TERMS.filter((t) => {
      const inGroup = active === "All" || t.group === active;
      const inQuery =
        !q ||
        t.term.toLowerCase().includes(q) ||
        t.short.toLowerCase().includes(q) ||
        t.detail.toLowerCase().includes(q);
      return inGroup && inQuery;
    });
  }, [query, active]);

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Reference</p>
          <h2>Glossary</h2>
          <p className="lede">
            Plain-language definitions for the terms used across this benchmark — so
            the decision evidence is readable without prior benchmarking background.
          </p>
        </div>
      </header>

      <div className="glossary-controls">
        <label className="glossary-search">
          <Search size={15} />
          <input
            type="search"
            placeholder="Search terms…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search glossary"
          />
        </label>
        <div className="glossary-filters" role="tablist" aria-label="Filter by group">
          {["All", ...GROUPS].map((g) => (
            <button
              key={g}
              type="button"
              role="tab"
              aria-selected={active === g}
              className={active === g ? "glossary-chip active" : "glossary-chip"}
              onClick={() => setActive(g)}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="glossary-empty">
          <BookOpen size={22} />
          <p>No terms match “{query}”.</p>
        </div>
      ) : (
        <div className="glossary-grid">
          {filtered.map((t) => (
            <article key={t.term} className="glossary-card">
              <div className="glossary-card-head">
                <h3>{t.term}</h3>
                <span className={`glossary-badge group-${t.group.toLowerCase()}`}>{t.group}</span>
              </div>
              <p className="glossary-short">{t.short}</p>
              <p className="glossary-detail">{t.detail}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
