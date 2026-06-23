"""Test script — Hosted Agent (Microsoft Agent Framework hosting, GA).

What this tests
---------------
The self-hosted runtime path. ``HRPolicyAgent`` (from
``src/agents/hr_policy_agent_af.py``) uses Agent Framework's ``Agent``
class wired to ``FoundryChatClient`` plus a ``@tool``-decorated
``search_hr_policies`` function. The agent autonomously decides when to
search and synthesizes answers from the retrieved chunks.

    Question ──► HRPolicyAgent.answer_question_async()
              ──► FoundryChatClient.invoke(prompt + tools)
              ──► gpt-4o decides to call @tool search_hr_policies
              ──► tool runs hybrid search against hr-policy-index
              ──► agent synthesizes grounded answer with citations

This is the same agent that runs inside the self-hosted container in
``src/hosted_agent/server.py`` (ResponsesHostServer); this script just
exercises the agent class directly so you don't have to deploy the
container.

Maps to
-------
- Pattern "Hosted" in ``docs/RetrievalPatterns.md``
- Microsoft Agent Framework "Step 6: Host Your Agent" GA hosting pattern
- The same agent loop as Lab 2.4 but with the developer hosting the
  runtime instead of using the Foundry Agent Service.

Required env:
    AZURE_AI_PROJECT_ENDPOINT
    AZURE_OPENAI_DEPLOYMENT_NAME    (defaults to gpt-4o)
    AZURE_SEARCH_ENDPOINT
    AZURE_SEARCH_INDEX_NAME         (defaults to hr-policy-index)
    AZURE_SEARCH_API_KEY            (or DefaultAzureCredential)

Usage
-----
    .venv/bin/python -m scripts.demo.test_pattern_hosted
    .venv/bin/python -m scripts.demo.test_pattern_hosted -q "What is the dress code?"
"""

from __future__ import annotations

import argparse
import asyncio
import os
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


async def _run_async(question: str) -> int:
    header(
        "Hosted Agent — Microsoft Agent Framework + FoundryChatClient",
        "Self-hosted runtime; agent autonomously calls @tool search_hr_policies",
    )

    required = (
        "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_SEARCH_ENDPOINT",
    )
    if not preflight_block("Hosted Agent preflight", required):
        return 2

    try:
        from src.agents.hr_policy_agent_af import HRPolicyAgent
        from src.config.search_config import search_cfg
    except Exception as exc:
        err(f"Failed to import Agent Framework HRPolicyAgent: {exc}")
        return 1

    stage("1. Construct the Agent Framework agent")
    agent = HRPolicyAgent(
        project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT", ""),
        model_deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", search_cfg.index_name),
        search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        search_api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        search_query_type=os.getenv("AI_SEARCH_QUERY_TYPE", "semantic"),
    )
    info(f"model = {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')}")
    info(f"index = {os.getenv('AZURE_SEARCH_INDEX_NAME', search_cfg.index_name)}")

    stage("2. Initialize the agent (one-time per process)")
    try:
        await agent.initialize()
    except Exception as exc:
        err(f"Agent initialization failed: {exc}")
        return 1

    stage("3. Ask the question — the agent decides when to call its tool")
    try:
        with timed("End-to-end latency"):
            result = await agent.answer_question_async(question)
    except Exception as exc:
        err(f"Agent invocation failed: {exc}")
        await agent.close()
        return 1

    print_chat_result(result)
    await agent.close()
    ok("Hosted Agent complete — autonomous tool use + grounded synthesis.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Live test of the Hosted Agent (Agent Framework).")
    parser.add_argument("--question", "-q", default=SAMPLE_CONTENT_QUESTION)
    args = parser.parse_args(argv)
    return asyncio.run(_run_async(args.question))


if __name__ == "__main__":
    sys.exit(main())
