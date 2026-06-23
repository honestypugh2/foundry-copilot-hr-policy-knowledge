"""Test script — Pattern B (Foundry Agent Service + MCPTool).

What this tests
---------------
The Foundry Agent Service path. ``HRPolicyAgent`` (from
``src/agents/hr_policy_agent.py``) publishes a ``PromptAgentDefinition``
whose only tool is an ``MCPTool`` against the Azure AI Search Knowledge
Base. With ``tool_choice="required"`` the model is forced to ground
every answer in retrieved policy chunks before responding.

    Question ──► HRPolicyAgent.answer_question_async()
              ──► Responses API with agent_reference=HRPolicyAgent
              ──► MCP tool: knowledge_base_retrieve (mandatory)
              ──► gpt-4o synthesis with inline policy citations

Maps to
-------
- Lab 2.4 — Microsoft Foundry Agentic Retrieval (the Foundry side of the
  Connected Agents pattern). The Fraud Analyst Agent in Lab 2.4 is the
  domain-swapped equivalent of ``HRPolicyAgent``.

Prerequisites
-------------
1. ``AGENT_SERVICE=foundry`` (or pass nothing — this script forces it locally).
2. The PromptAgent must be provisioned. Run once:
       uv run python -m src.agents.create_foundry_agent
3. Required env:
       AZURE_AI_PROJECT_ENDPOINT
       AZURE_OPENAI_DEPLOYMENT_NAME    (defaults to gpt-4o)
       AZURE_SEARCH_ENDPOINT

Usage
-----
    .venv/bin/python -m scripts.demo.test_pattern_b
    .venv/bin/python -m scripts.demo.test_pattern_b -q "How much PTO do part-time employees accrue?"
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
    warn,
)


async def _run_async(question: str) -> int:
    header(
        "Pattern B — Foundry Agent Service + MCPTool",
        "PromptAgent with tool_choice='required' (force-grounded synthesis)",
    )

    required = (
        "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_SEARCH_ENDPOINT",
    )
    if not preflight_block("Pattern B preflight", required):
        return 2

    # Force the orchestrator into Foundry mode for this run (without
    # mutating .env on disk).
    os.environ.setdefault("AGENT_SERVICE", "foundry")

    try:
        from src.agents.hr_policy_agent import HRPolicyAgent
    except Exception as exc:
        err(f"Failed to import HRPolicyAgent (Foundry): {exc}")
        return 1

    stage("1. Construct the agent client")
    agent = HRPolicyAgent(use_agent=True)
    info(f"project_endpoint = {agent.project_endpoint}")
    info(f"model            = {agent.model_deployment_name}")

    stage("2. Initialize — ensure PromptAgent exists in the Foundry portal")
    try:
        await agent.initialize()
    except Exception as exc:
        err(f"Foundry agent initialization failed: {exc}")
        info("Run: uv run python -m src.agents.create_foundry_agent")
        return 1

    if agent._openai is None:  # type: ignore[attr-defined]
        warn(
            "Foundry client unavailable — the agent will fall back to local "
            "search. Provision the PromptAgent first: "
            "uv run python -m src.agents.create_foundry_agent"
        )

    stage("3. Ask the question — MCP tool runs server-side, gpt-4o synthesizes")
    try:
        with timed("End-to-end latency"):
            result = await agent.answer_question_async(question)
    except Exception as exc:
        err(f"Agent invocation failed: {exc}")
        await agent.close()
        return 1

    print_chat_result(result)
    await agent.close()
    ok("Pattern B complete — force-grounded answer with inline citations.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Live test of Pattern B (Foundry Agent + MCP).")
    parser.add_argument("--question", "-q", default=SAMPLE_CONTENT_QUESTION)
    args = parser.parse_args(argv)
    return asyncio.run(_run_async(args.question))


if __name__ == "__main__":
    sys.exit(main())
