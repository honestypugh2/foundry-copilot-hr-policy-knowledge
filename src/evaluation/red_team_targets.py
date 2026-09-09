"""Target callbacks that expose the HR-policy agents to the AI Red Teaming Agent.

Additive example for the red-teaming / continuous-evaluation story — this does
not change any authoritative benchmark artifact. Each builder returns an async
callback in the Azure AI Evaluation "advanced" (OpenAI chat protocol) form and
reuses the same agents the benchmark measures, so scans exercise the real paths.

Targets:
  b       -> Pattern B Foundry prompt agent (HRPolicyAgent + MCP knowledge base)
  hosted  -> Foundry hosted agent (deployed container, Responses endpoint)
  copilot -> Copilot Studio published agent (Direct Line), lane-selectable
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

AnswerCallable = Callable[[str], Awaitable[dict[str, Any]]]
AdvancedCallback = Callable[..., Awaitable[dict[str, Any]]]


def _latest_user_message(messages: Any) -> str:
    items = getattr(messages, "messages", messages)
    last_content = ""
    for message in items:
        role = getattr(message, "role", None) or (message.get("role") if isinstance(message, dict) else None)
        content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
        if content:
            last_content = str(content)
        if role == "user" and content:
            return str(content)
    return last_content


def _wrap(answer_fn: AnswerCallable) -> AdvancedCallback:
    async def callback(messages: Any, stream: bool = False, session_state: Any = None, context: Any = None) -> dict[str, Any]:
        query = _latest_user_message(messages)
        result = await answer_fn(query)
        return {"messages": [{"role": "assistant", "content": str(result.get("answer") or "")}]}

    return callback


def build_foundry_prompt_target() -> AdvancedCallback:
    """Pattern B: Foundry Agent Service prompt agent (HRPolicyAgent)."""
    from src.agents.hr_policy_agent import HRPolicyAgent

    agent = HRPolicyAgent()

    async def answer(query: str) -> dict[str, Any]:
        return await agent.answer_question_async(query)

    return _wrap(answer)


def build_hosted_target(agent_name: str | None = None) -> AdvancedCallback:
    """Hosted: the deployed Foundry hosted (Agent Framework container) agent."""
    from src.benchmarking.adapters.foundry_hosted import build_foundry_hosted_answer

    name = agent_name or os.getenv("AZURE_AI_HOSTED_AGENT_NAME", "hr-policy-agent")
    return _wrap(build_foundry_hosted_answer(name))


def build_copilot_target(lane: str | None = None) -> AdvancedCallback:
    """Copilot Studio published agent over Direct Line (local scan only).

    ``lane`` selects per-lane env config by suffix (e.g. A / A2 / C):
    COPILOT_STUDIO_AGENT_SCHEMA_<LANE>, COPILOT_STUDIO_TOKEN_ENDPOINT_<LANE>,
    COPILOT_STUDIO_TOKEN_SECRET_<LANE> / COPILOT_STUDIO_DIRECTLINE_SECRET_<LANE>.
    """
    from src.copilot_studio.service import CopilotStudioService

    suffix = (lane or "").strip().upper()

    def _env(name: str) -> str | None:
        return (os.getenv(f"{name}_{suffix}") if suffix else None) or os.getenv(name)

    service = CopilotStudioService(
        environment_id=os.getenv("COPILOT_STUDIO_ENVIRONMENT_ID"),
        agent_schema=_env("COPILOT_STUDIO_AGENT_SCHEMA"),
        token_endpoint=_env("COPILOT_STUDIO_TOKEN_ENDPOINT"),
        directline_secret=_env("COPILOT_STUDIO_TOKEN_SECRET") or _env("COPILOT_STUDIO_DIRECTLINE_SECRET"),
    )
    if not service.is_configured:
        raise ValueError(
            "Copilot Studio target not configured; set COPILOT_STUDIO_ENVIRONMENT_ID and "
            "COPILOT_STUDIO_AGENT_SCHEMA[_LANE] plus a token endpoint or Direct Line secret."
        )
    return _wrap(service.ask)


def build_target(target: str, *, agent_name: str | None = None, lane: str | None = None) -> AdvancedCallback:
    key = target.lower()
    if key in ("b", "prompt", "foundry-prompt"):
        return build_foundry_prompt_target()
    if key in ("hosted", "foundry-hosted"):
        return build_hosted_target(agent_name)
    if key in ("copilot", "copilot-studio"):
        return build_copilot_target(lane)
    raise ValueError(f"Unknown red-team target {target!r} (use b | hosted | copilot)")
