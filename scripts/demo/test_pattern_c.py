"""Test script — Pattern C (Dual-Tool Routing / deterministic locator).

What this tests
---------------
The ``POST /api/lookup`` shape: a direct hybrid search over the same
``hr-policy-index`` that Patterns A and B use, but returning only the
metadata fields (``policy_number``, ``parent_title``,
``metadata_storage_name``, ``metadata_storage_path``, ``blob_url``,
``score``). No LLM. No Foundry agent. No MCP call.

    Locator question ──► glossary expand ──► hybrid search ──► metadata-only JSON

This is what Copilot Studio's ``lookupHRPolicyDocument`` REST tool
(imported from ``copilot/openapi-lookup-v2.json``) invokes when the
planner decides a turn is a "WHERE is this document?" intent.

Maps to
-------
- Lab 2.1 Option 2 — Custom HTTP / Power Automate flow (functionally
  equivalent; same shape: agent calls custom HTTP, parses JSON).
- Lab 2.1 Option 3 — Custom Connector / Swagger
  (``copilot/openapi-lookup-v2.json`` is exactly this).
- Lab 2.4 — the "quick lookup" half of the Connected Agents pattern.

Compare with the native-citation alternative documented in
``docs/CopilotStudioLookupRouting.md#pattern-c-vs-native-citations``.

Usage
-----
    .venv/bin/python -m scripts.demo.test_pattern_c
    .venv/bin/python -m scripts.demo.test_pattern_c -q "What's the file path for the Code of Ethics?"

Required env:
    AZURE_SEARCH_ENDPOINT
    AZURE_SEARCH_API_KEY (or DefaultAzureCredential)
"""

from __future__ import annotations

import argparse
import sys
import time

from dotenv import load_dotenv

from scripts.demo._common import (
    SAMPLE_LOCATOR_QUESTION,
    err,
    header,
    info,
    ok,
    preflight_block,
    print_lookup_result,
    stage,
    timed,
)


def run(question: str) -> int:
    header(
        "Pattern C — Dual-Tool Routing (deterministic locator)",
        "Mirrors POST /api/lookup → metadata-only JSON, no LLM",
    )

    if not preflight_block("Pattern C preflight", ("AZURE_SEARCH_ENDPOINT",)):
        return 2

    try:
        from src.search.integrated_vectorization_search import (
            IntegratedVectorizationSearchService,
        )
        from src.search.search_service import expand_query_with_glossary
    except Exception as exc:
        err(f"Failed to import search modules: {exc}")
        return 1

    stage("1. Glossary expansion", "same query rewrite as Pattern A")
    expanded = expand_query_with_glossary(question)
    info(f'Original : "{question}"')
    info(f'Expanded : "{expanded}"')

    stage("2. Hybrid search → metadata-only projection")
    start = time.time()
    try:
        with timed("Search latency"):
            iv = IntegratedVectorizationSearchService()
            hits = iv.search(expanded, top=3)
    except Exception as exc:
        err(f"Search call failed: {exc}")
        return 1

    documents = []
    for h in hits:
        documents.append({
            "policy_number": h.get("policy_number", ""),
            "parent_title": h.get("parentTitle", h.get("title", "")),
            "metadata_storage_name": h.get("fileName", ""),
            "metadata_storage_path": h.get("filePath", ""),
            "blob_url": h.get("blob_url", ""),
            "score": h.get("score", 0.0),
        })

    elapsed_ms = int((time.time() - start) * 1000)
    payload = {
        "query": question,
        "expanded_query": expanded,
        "documents": documents,
        "total": len(documents),
        "processing_time_ms": elapsed_ms,
    }
    print_lookup_result(payload)

    if not documents:
        err("No documents matched — the locator tool would return found=false.")
        return 1

    stage("3. Routing levers (for the Copilot Studio side)")
    info("Lever 1: Agent instructions distinguish LOCATION vs CONTENT intents.")
    info("Lever 2: Tool description mirrors honestypugh2/foundry-copilot-search-validate verbatim.")
    info("See docs/CopilotStudioLookupRouting.md.")

    ok("Pattern C complete — sub-second, deterministic, URL-verbatim answer.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Live test of Pattern C (Dual-Tool Routing).")
    parser.add_argument("--question", "-q", default=SAMPLE_LOCATOR_QUESTION)
    args = parser.parse_args(argv)
    return run(args.question)


if __name__ == "__main__":
    sys.exit(main())
