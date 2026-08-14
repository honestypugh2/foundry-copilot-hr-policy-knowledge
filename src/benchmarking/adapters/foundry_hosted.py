"""Adapter for the deployed Foundry hosted agent (managed-runtime boundary).

Invokes the published hosted agent through its dedicated Responses endpoint,
which is a different measurement boundary than the in-process Agent Framework
adapter: it includes the managed hosted runtime and network hop.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.benchmarking.adapters.agent import AgentAnswerAdapter

# Match "[Policy 10000 - Title]" and bare "Policy 10000 — Title"/"Policy 10000: Title";
# allow hyphen, en/em dash, or colon, and 3-6 digit policy numbers.
_POLICY_CITATION = re.compile(
    r"\[?Policy\s+(?P<number>\d{3,6})\s*[-–—:]\s*(?P<title>[^\]\n]+?)\]?(?=[.,;\n]|$)"
)
# Foundry hosted-agent Responses protocol version; hosted agents reject others.
_HOSTED_API_VERSION = "2025-05-15-preview"
_HOSTED_TOKEN_SCOPE = "https://ai.azure.com/.default"


def build_foundry_hosted_answer(
    agent_name: str,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Return an async answer callable that invokes the deployed hosted agent."""
    endpoint = (
        os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
        or os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
    ).rstrip("/")
    if not endpoint:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT is required to invoke the deployed hosted agent"
        )
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")
    base_url = f"{endpoint}/agents/{agent_name}/endpoint/protocols/openai"
    # Auto-refreshing bearer token so long runs do not fail on token expiry.
    token_provider = get_bearer_token_provider(
        AzureCliCredential(process_timeout=30), _HOSTED_TOKEN_SCOPE
    )
    client = AzureOpenAI(
        base_url=base_url,
        azure_ad_token_provider=token_provider,
        api_version=_HOSTED_API_VERSION,
    )

    def _call(query: str) -> dict[str, Any]:
        response = client.responses.create(model=model, input=query)
        text = str(getattr(response, "output_text", "") or "")
        citations = []
        seen: set[str] = set()
        for match in _POLICY_CITATION.finditer(text):
            number = match.group("number")
            if number in seen:
                continue
            seen.add(number)
            citations.append(
                {"policy_number": number, "title": match.group("title").strip().rstrip(".]")}
            )
        usage_obj = getattr(response, "usage", None)
        usage: dict[str, Any] = {}
        if usage_obj is not None:
            for key in ("input_tokens", "output_tokens"):
                value = getattr(usage_obj, key, None)
                if value is not None:
                    usage[key] = int(value)
        return {
            "answer": text,
            "citations": citations,
            "usage": usage,
            "response_id": getattr(response, "id", None),
            "status": "success",
        }

    async def answer(query: str) -> dict[str, Any]:
        return await asyncio.to_thread(_call, query)

    return answer


def build_foundry_hosted_adapter(agent_name: str) -> AgentAnswerAdapter:
    return AgentAnswerAdapter(
        build_foundry_hosted_answer(agent_name),
        pattern="Hosted",
        invocation_path=f"foundry_hosted_agent:{agent_name}",
    )
