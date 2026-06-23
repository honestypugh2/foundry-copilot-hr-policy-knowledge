"""Test script — Pattern A (Direct Knowledge Base) ★ default.

What this tests
---------------
The exact code path that backs Copilot Studio's native "Add knowledge →
Azure AI Search" connector against ``hr-policy-index``:

    Question ──► glossary expansion ──► hybrid search (BM25 + vector + semantic)
              ──► top-K hits ──► deterministic concatenation (no LLM)

This mirrors what ``src/backend/main.py:/api/chat`` returns when
``ORCHESTRATOR_PATTERN=A`` (the project default), and what Copilot Studio
itself runs when wired per
``docs/CopilotStudioIntegration.md#pattern-a-wiring``.

Maps to
-------
- Lab 1.4 — Use Azure AI Search in Copilot Studio
- Lab 2.1 Option 1 — Connect Azure AI Search as Knowledge Source
- Lab 2.3 Exercise 4 — Connect (any) AI Search index to Copilot Studio
- Lab 2.4 "Quick Lookups" surface (when backed by AI Search rather than an
  uploaded markdown file)

Usage
-----
    .venv/bin/python -m scripts.demo.test_pattern_a
    .venv/bin/python -m scripts.demo.test_pattern_a --question "How much PTO do I accrue?"

Required env (in ``.env`` or shell):
    AZURE_SEARCH_ENDPOINT
    AZURE_SEARCH_INDEX_NAME       (defaults to ``hr-policy-index``)
    AZURE_SEARCH_API_KEY          (or DefaultAzureCredential)
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from scripts.demo._common import (
    SAMPLE_CONTENT_QUESTION,
    err,
    header,
    info,
    ok,
    preflight_block,
    print_chat_result,
    stage,
    timed,
)


def run(question: str) -> int:
    header(
        "Pattern A — Direct Knowledge Base (★ default)",
        "Mirrors Copilot Studio Knowledge Source → Azure AI Search",
    )

    if not preflight_block("Pattern A preflight", ("AZURE_SEARCH_ENDPOINT",)):
        return 2

    # Import after preflight so a missing dep fails with a sharper message.
    try:
        from src.search.integrated_vectorization_search import (
            IntegratedVectorizationSearchService,
        )
        from src.search.search_service import expand_query_with_glossary
    except Exception as exc:  # pragma: no cover - environment guard
        err(f"Failed to import search modules: {exc}")
        return 1

    stage("1. Expand the query with the HR glossary", "synonym map applied at query time")
    expanded = expand_query_with_glossary(question)
    info(f'Original : "{question}"')
    info(f'Expanded : "{expanded}"')

    stage("2. Run hybrid search (BM25 + vector + semantic ranker)")
    try:
        with timed("Search latency"):
            search = IntegratedVectorizationSearchService()
            hits = search.search(expanded, top=3)
    except Exception as exc:
        err(f"Search call failed: {exc}")
        info("Verify AZURE_SEARCH_ENDPOINT and that hr-policy-index is populated.")
        return 1

    if not hits:
        err("No hits returned — is the index populated?")
        info("Run: uv run python scripts/index_knowledge_base_integrated_vectorization.py")
        return 1
    ok(f"{len(hits)} hit(s) returned")

    stage("3. Compose the deterministic answer (no LLM, no Foundry)")
    citations: list[dict] = []
    policy_refs: list[str] = []
    snippets: list[str] = []
    for hit in hits:
        pn = hit.get("policy_number", "")
        title = hit.get("title", "") or hit.get("parentTitle", "")
        content = hit.get("content", "")
        if pn and title:
            citations.append({"policy_number": pn, "title": title})
            policy_refs.append(f"Policy {pn} - {title}")
        if content:
            snippets.append(f"[Policy {pn} - {title}]\n{content[:400].strip()}")

    result = {
        "answer": "\n\n".join(snippets) or "No extractable content in top hits.",
        "citations": citations,
        "policy_references": list(dict.fromkeys(policy_refs)),
        "confidence": 0.7 if citations else 0.4,
    }
    print_chat_result(result)
    ok("Pattern A complete — this is what Copilot Studio returns natively.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Live test of Pattern A (Direct KB).")
    parser.add_argument("--question", "-q", default=SAMPLE_CONTENT_QUESTION)
    args = parser.parse_args(argv)
    return run(args.question)


if __name__ == "__main__":
    sys.exit(main())
