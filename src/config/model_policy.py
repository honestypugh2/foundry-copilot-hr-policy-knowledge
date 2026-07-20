"""
Central model policy — single source of truth for model deployment names.

Replaces the ``gpt-4o`` literals that were previously scattered across the
agents, orchestrator, hosted runtime, and search config. GPT-4o was retired
for Copilot Studio generative orchestration (October 2025). This repo's
infrastructure deploys **GPT-5-mini** as the default chat model, with
**GPT-4.1**, **GPT-5**, and **Claude** also usable where they have regional
capacity in Microsoft Foundry.

The value returned here is a *model deployment name* in your Microsoft
Foundry / Azure OpenAI resource, not a raw model id. Override it to match
what you have deployed:

    FOUNDRY_MODEL=gpt-5
    # or
    AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
    # or a non-OpenAI reasoning core, e.g. claude-sonnet-4-6

Usage:
    from src.config.model_policy import get_chat_model, get_embedding_model

    model = get_chat_model()                 # env-driven, defaults to gpt-5-mini
    model = get_chat_model("gpt-5")          # explicit override wins
"""

from __future__ import annotations

import os
from typing import Optional

# Default answer-synthesis / reasoning model deployment name.
# GPT-4o is retired for Copilot Studio generative orchestration; this repo's
# infra deploys gpt-5-mini as the default. Override via env to use GPT-4.1,
# GPT-5, or Claude (subject to regional capacity).
DEFAULT_CHAT_MODEL = "gpt-5-mini"

# Default embedding model deployment name (matches search_config.json).
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_chat_model(override: Optional[str] = None) -> str:
    """Resolve the chat/reasoning model deployment name.

    Precedence: explicit ``override`` → ``FOUNDRY_MODEL`` →
    ``AZURE_OPENAI_DEPLOYMENT_NAME`` → ``AZURE_OPENAI_DEPLOYMENT`` →
    :data:`DEFAULT_CHAT_MODEL`.
    """
    return (
        override
        or os.getenv("FOUNDRY_MODEL")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or DEFAULT_CHAT_MODEL
    )


def get_embedding_model(override: Optional[str] = None) -> str:
    """Resolve the embedding model deployment name.

    Precedence: explicit ``override`` → ``AZURE_OPENAI_EMBEDDING_DEPLOYMENT``
    → :data:`DEFAULT_EMBEDDING_MODEL`.
    """
    return (
        override
        or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or DEFAULT_EMBEDDING_MODEL
    )
