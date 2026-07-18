"""Storytelling demo — walk the decision tree, exercise every pattern.

Tells the four-act story behind ``docs/RetrievalPatterns.md`` and
``docs/LabCoverage.md`` by running each pattern back-to-back against
the same HR-policy index and narrating the trade-offs.

The four acts
-------------
Act 1 — "I just want answers."          → Pattern A (Lab 1.4, Lab 2.1 Option 1)
Act 2 — "I need force-grounded synthesis." → Pattern B (Lab 2.4 Foundry side)
Act 3 — "I just want to find the document." → Pattern C vs native citations
                                                 (Lab 2.1 Options 2/3, Lab 2.4 quick path)
Act 4 — "I want to host the runtime myself." → Hosted Agent
                                                 (Agent Framework hosting, GA)

What the demo does
------------------
For each act it:
  1. Prints the decision-tree branch being taken.
  2. Identifies which upstream lab the path comes from.
  3. Runs the corresponding ``test_pattern_*`` flow against the live
     index (skipping gracefully if Foundry isn't provisioned).
  4. Prints a side-by-side latency / shape summary at the end.

Usage
-----
    .venv/bin/python -m scripts.demo.demo_decision_tree
    .venv/bin/python -m scripts.demo.demo_decision_tree --skip-b --skip-hosted
    .venv/bin/python -m scripts.demo.demo_decision_tree --content "What is the dress code?" \\
                                                         --locator "Where is the dress code policy?"

Flags
-----
    --skip-a / --skip-b / --skip-c / --skip-hosted     skip specific acts
    --content TEXT     override the content question (Acts 1, 2, 4)
    --locator TEXT     override the locator question (Act 3)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

from dotenv import load_dotenv

from scripts.demo._common import (
    SAMPLE_CONTENT_QUESTION,
    SAMPLE_HYBRID_QUESTION,
    SAMPLE_LOCATOR_QUESTION,
    err,
    header,
    info,
    ok,
    stage,
    timed,
    warn,
)

# Re-use the act runners so the demo and the per-pattern scripts stay in sync.
from scripts.demo import (
    test_pattern_a,
    test_pattern_b,
    test_pattern_c,
    test_pattern_hosted,
)


DECISION_TREE_ART = r"""
            New HR Q&A scenario
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
  Need answer                  Need answer
  synthesis?  No               synthesis?  Yes
        │                        │
        ▼                        ▼
  Locator question         Need an LLM agent?
        │                  ┌─────┴─────┐
  ┌─────┴──────┐           No          Yes
  │            │           │             │
Native       Pattern C     ▼             ▼
citations    POST          Pattern A    Self-host
(★ Pattern A   /api/lookup  (★)         runtime?
 KB on        deterministic               │
 SharePoint                        ┌──────┴──────┐
 or AI                             No            Yes
 Search w/                         │              │
 blob_url)                         ▼              ▼
                              Pattern B      Hosted Agent
                              Foundry        (Agent Framework
                              PromptAgent     hosting, GA)
                              + MCPTool
"""


# ---------------------------------------------------------------------------
# Act runners
# ---------------------------------------------------------------------------

def act_1_pattern_a(content_q: str) -> Optional[int]:
    header(
        "ACT 1 — \"I just want answers, fast.\"",
        "Decision-tree path: synthesis=Yes → LLM agent=No → ★ Pattern A",
    )
    info("Story: Lab 1.4 onboards an AI Search index into Copilot Studio in one")
    info("       click. That click is what this code path emulates: hybrid")
    info("       search (BM25 + vector + semantic ranker) returned to the")
    info("       caller with no LLM in the path. Lab 2.1 Option 1 is the same")
    info("       wiring with the index design called out explicitly.")
    info("")
    info("Maps to: Lab 1.4, Lab 2.1 Option 1")
    info("Code:    src/backend/main.py:_pattern_a_answer + IntegratedVectorizationSearchService")
    return test_pattern_a.run(content_q)


async def act_2_pattern_b(content_q: str) -> Optional[int]:
    header(
        "ACT 2 — \"I need force-grounded synthesis.\"",
        "Decision-tree path: synthesis=Yes → LLM agent=Yes → self-host=No → Pattern B",
    )
    info("Story: Lab 2.4 builds a Foundry Fraud Analyst Agent with an MCP tool")
    info("       over a multi-source Knowledge Base. This repo's HRPolicyAgent")
    info("       (Pattern B) is the domain-swapped equivalent — single source")
    info("       (hr-policy-index) but the same PromptAgent + MCPTool +")
    info("       tool_choice='required' contract.")
    info("")
    info("Maps to: Lab 2.4 — Microsoft Foundry Agentic Retrieval (Foundry side)")
    info("Code:    src/agents/hr_policy_agent.py + src/agents/create_foundry_agent.py")
    info("")
    warn("Pattern B requires a provisioned Foundry PromptAgent.")
    warn("If you haven't run `uv run python -m src.agents.create_foundry_agent`,")
    warn("the agent will fall back to local search and emit a warning.")
    return await test_pattern_b._run_async(content_q)


def act_3a_native_citations() -> None:
    stage("3a. Alternative path — native Copilot Studio citations")
    info("Before Pattern C, ask: does the source surface its own deep link?")
    info("  • SharePoint connector: citation = direct deep link to the file.")
    info("  • Azure AI Search (Pattern A) with blob_url mapped: citation card")
    info("    surfaces the URL automatically.")
    info("If yes, the locator answer is free — every Pattern A response")
    info("already includes a click-through link. No new tool to wire.")
    info("")
    info("Reference: docs/CopilotStudioLookupRouting.md#pattern-c-vs-native-citations")


def act_3b_pattern_c(locator_q: str) -> Optional[int]:
    stage("3b. Pattern C — when native citations aren't enough")
    info("Use Pattern C when you need any of:")
    info("  • Sub-second latency on locator queries (no LLM call).")
    info("  • The URL in the answer body verbatim (not in a citation footer).")
    info("  • Deterministic / auditable output — the exact blob_url, never paraphrased.")
    info("  • Zero LLM cost on high-volume locator traffic.")
    info("  • Your source isn't a citation-friendly KB.")
    info("")
    info("Maps to: Lab 2.1 Option 2 (HTTP flow) + Option 3 (Swagger connector),")
    info("         Lab 2.4 \"quick lookup\" half of the Connected Agents pattern")
    info("Code:    src/backend/main.py:/api/lookup + copilot/openapi-lookup-v2.json")
    return test_pattern_c.run(locator_q)


def act_3_locator(locator_q: str) -> Optional[int]:
    header(
        "ACT 3 — \"I just want to find the document.\"",
        "Decision-tree path: synthesis=No → locator → native citations OR Pattern C",
    )
    act_3a_native_citations()
    return act_3b_pattern_c(locator_q)


async def act_4_hosted(content_q: str) -> Optional[int]:
    header(
        "ACT 4 — \"I want to host the runtime myself.\"",
        "Decision-tree path: synthesis=Yes → LLM agent=Yes → self-host=Yes → Hosted Agent",
    )
    info("Story: Agent Framework's GA hosting pattern (\"Step 6: Host Your")
    info("       Agent\") lets you run the exact same agent loop as Pattern B")
    info("       inside your own container, with custom auth, side-cars, and")
    info("       direct control of the runtime. This script exercises the")
    info("       agent class directly so you don't have to deploy the")
    info("       container in src/hosted_agent/.")
    info("")
    info("Maps to: Microsoft Agent Framework Step 6 (Host Your Agent)")
    info("Code:    src/agents/hr_policy_agent_af.py + src/hosted_agent/server.py")
    return await test_pattern_hosted._run_async(content_q)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

async def _run(
    *,
    content_q: str,
    locator_q: str,
    skip_a: bool,
    skip_b: bool,
    skip_c: bool,
    skip_hosted: bool,
) -> int:
    header(
        "Decision-Tree Demo — Ask HR Policy Knowledge Agent",
        "Walks docs/RetrievalPatterns.md and docs/LabCoverage.md end-to-end",
    )
    print(DECISION_TREE_ART)
    info("Reference docs:")
    info("  • README.md — Decision tree + pattern table")
    info("  • docs/RetrievalPatterns.md — full pattern detail")
    info("  • docs/LabCoverage.md — cross-walk to Azure/Copilot-Studio-and-Azure labs")
    info("  • docs/CopilotStudioLookupRouting.md — Pattern C vs native citations")

    results: dict[str, dict[str, object]] = {}

    if not skip_a:
        with timed("Act 1 wall-clock") as box:
            rc = act_1_pattern_a(content_q)
        results["A"] = {"rc": rc, "elapsed_ms": box["elapsed_ms"]}
    else:
        warn("Skipping Act 1 (Pattern A) per --skip-a")

    if not skip_b:
        with timed("Act 2 wall-clock") as box:
            rc = await act_2_pattern_b(content_q)
        results["B"] = {"rc": rc, "elapsed_ms": box["elapsed_ms"]}
    else:
        warn("Skipping Act 2 (Pattern B) per --skip-b")

    if not skip_c:
        with timed("Act 3 wall-clock") as box:
            rc = act_3_locator(locator_q)
        results["C"] = {"rc": rc, "elapsed_ms": box["elapsed_ms"]}
    else:
        warn("Skipping Act 3 (Pattern C) per --skip-c")

    if not skip_hosted:
        with timed("Act 4 wall-clock") as box:
            rc = await act_4_hosted(content_q)
        results["Hosted"] = {"rc": rc, "elapsed_ms": box["elapsed_ms"]}
    else:
        warn("Skipping Act 4 (Hosted Agent) per --skip-hosted")

    # ---- Curtain call ------------------------------------------------------
    header("CURTAIN CALL — side-by-side summary", "Pattern · result · latency · lab origin")

    lab_origin = {
        "A": "Lab 1.4 / Lab 2.1 Option 1",
        "B": "Lab 2.4 (Foundry side)",
        "C": "Lab 2.1 Options 2 & 3 / Lab 2.4 (quick path)",
        "Hosted": "Agent Framework GA hosting",
    }
    fmt = "  {pat:<8} {status:<8} {latency:>10}  {lab}"
    print()
    print(fmt.format(pat="Pattern", status="Result", latency="Latency", lab="Lab origin"))
    print("  " + "-" * 76)
    for key, info_dict in results.items():
        rc = info_dict.get("rc")
        elapsed = info_dict.get("elapsed_ms", 0.0)
        if rc == 0:
            status = "ok"
        elif rc == 2:
            status = "skipped"
        else:
            status = "failed"
        latency = f"{float(elapsed):.0f} ms" if isinstance(elapsed, (int, float)) else "n/a"
        print(fmt.format(pat=key, status=status, latency=latency, lab=lab_origin.get(key, "")))

    print()
    ok("Demo complete. Reread docs/RetrievalPatterns.md with the live results in mind.")

    # Non-zero exit only when an *enabled* pattern actually failed (not skipped).
    failed = [k for k, v in results.items() if v.get("rc") not in (0, 2, None)]
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--content", default=SAMPLE_CONTENT_QUESTION,
                        help="Content question for Acts 1, 2, 4")
    parser.add_argument("--locator", default=SAMPLE_LOCATOR_QUESTION,
                        help="Locator question for Act 3")
    parser.add_argument("--hybrid", default=SAMPLE_HYBRID_QUESTION,
                        help="(Reserved) hybrid question for future Act 5")
    parser.add_argument("--skip-a", action="store_true")
    parser.add_argument("--skip-b", action="store_true")
    parser.add_argument("--skip-c", action="store_true")
    parser.add_argument("--skip-hosted", action="store_true")
    args = parser.parse_args(argv)

    try:
        return asyncio.run(_run(
            content_q=args.content,
            locator_q=args.locator,
            skip_a=args.skip_a,
            skip_b=args.skip_b,
            skip_c=args.skip_c,
            skip_hosted=args.skip_hosted,
        ))
    except KeyboardInterrupt:
        err("Aborted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
