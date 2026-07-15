"""
Foundry memory store provisioning (P2.7 — production-ready memory).

Wraps ``azure-ai-projects`` (2.3.0+) ``beta.memory_stores`` to give the HR
policy agent persistent, per-user context with three capabilities:

- **User profile** — remembers an employee's stable preferences (e.g. they are
  part-time, so PTO answers should reference the part-time policy).
- **Chat summary** — condenses prior turns so multi-question conversations stay
  coherent without resending full history.
- **Procedural memory** — remembers *how your org actually handles* recurring
  procedures (leave requests, access requests, escalation triage) and reapplies
  them consistently instead of reinventing them each run.

A **time-to-live (TTL)** is applied so memories are automatically retired. This
is important for HR data: unbounded retention of personal/time-sensitive context
is a compliance risk, so the default is a bounded 30-day window.

Notes:
    * In ``azure-ai-projects`` 2.3.0 ``default_ttl_seconds`` is a
      :class:`datetime.timedelta` (it was an ``int`` of seconds in 2.2.0).
    * ``MemoryStoreDefaultOptions`` defaults any field you don't set to
      ``False``, so this module always sets every field explicitly.
    * Memory store operations live on the ``.beta`` sub-client, which does not
      require ``allow_preview=True``.

Reference:
    https://learn.microsoft.com/azure/foundry/agents/concepts/memory
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Optional

from src.config.model_policy import get_chat_model, get_embedding_model

if TYPE_CHECKING:
    from azure.ai.projects.models import (
        MemoryStoreDefaultDefinition,
        MemoryStoreDefaultOptions,
    )

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_STORE_NAME = "hr-policy-memory"
DEFAULT_TTL_DAYS = 30

try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import (
        MemoryStoreDefaultDefinition,
        MemoryStoreDefaultOptions,
    )
    from azure.identity import DefaultAzureCredential

    MEMORY_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional install
    MEMORY_SDK_AVAILABLE = False
    AIProjectClient = None  # type: ignore[assignment,misc]
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    logger.warning("azure-ai-projects not installed; memory store provisioning unavailable.")


def build_memory_options(
    *,
    ttl_days: int = DEFAULT_TTL_DAYS,
    user_profile_enabled: bool = True,
    chat_summary_enabled: bool = True,
    procedural_memory_enabled: bool = True,
    user_profile_details: Optional[str] = None,
) -> "MemoryStoreDefaultOptions":
    """Build :class:`MemoryStoreDefaultOptions` with an explicit TTL.

    Every field is set explicitly because the SDK defaults unset fields to
    ``False`` rather than the documented defaults.

    Args:
        ttl_days: Retention window in days. ``0`` means memories never expire —
            avoid for HR data.
    """
    if not MEMORY_SDK_AVAILABLE:
        raise RuntimeError("azure-ai-projects is required to build memory options.")

    kwargs: dict[str, Any] = {
        "user_profile_enabled": user_profile_enabled,
        "chat_summary_enabled": chat_summary_enabled,
        "procedural_memory_enabled": procedural_memory_enabled,
        "default_ttl_seconds": timedelta(days=ttl_days),
    }
    if user_profile_details is not None:
        kwargs["user_profile_details"] = user_profile_details
    return MemoryStoreDefaultOptions(**kwargs)  # type: ignore[misc]


def build_memory_definition(
    *,
    chat_model: Optional[str] = None,
    embedding_model: Optional[str] = None,
    options: Optional["MemoryStoreDefaultOptions"] = None,
) -> "MemoryStoreDefaultDefinition":
    """Build a :class:`MemoryStoreDefaultDefinition` for the HR agent.

    Model deployment names resolve through :mod:`src.config.model_policy` so
    memory extraction uses the same governed model policy as the agent.
    """
    if not MEMORY_SDK_AVAILABLE:
        raise RuntimeError("azure-ai-projects is required to build a memory definition.")

    return MemoryStoreDefaultDefinition(  # type: ignore[misc]
        chat_model=get_chat_model(chat_model),
        embedding_model=get_embedding_model(embedding_model),
        options=options if options is not None else build_memory_options(),
    )


def _resolve_credential() -> Any:
    try:
        from azure.identity import AzureCliCredential

        return AzureCliCredential(process_timeout=30)
    except Exception:  # pragma: no cover
        return DefaultAzureCredential() if DefaultAzureCredential else None


def provision_memory_store(
    *,
    project_endpoint: Optional[str] = None,
    name: str = DEFAULT_MEMORY_STORE_NAME,
    description: str = "HR policy agent memory with procedural recall and bounded retention.",
    ttl_days: int = DEFAULT_TTL_DAYS,
    chat_model: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> Any:
    """Create (or update) the HR policy memory store in a Foundry project.

    Returns the created memory store object.
    """
    if not MEMORY_SDK_AVAILABLE:
        raise RuntimeError("azure-ai-projects is required to provision a memory store.")

    endpoint = (
        project_endpoint
        or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
        or os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
    )
    if not endpoint:
        raise ValueError(
            "No Foundry project endpoint. Set AZURE_AI_PROJECT_ENDPOINT."
        )

    options = build_memory_options(ttl_days=ttl_days)
    definition = build_memory_definition(
        chat_model=chat_model,
        embedding_model=embedding_model,
        options=options,
    )

    credential = _resolve_credential()
    with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:  # type: ignore[misc]
        store = project_client.beta.memory_stores.create(
            name=name,
            description=description,
            definition=definition,
        )
    logger.info(
        "Memory store '%s' provisioned (ttl=%d days, procedural=on)", name, ttl_days
    )
    return store


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Provision the HR policy memory store.")
    parser.add_argument("--name", default=DEFAULT_MEMORY_STORE_NAME)
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    parser.add_argument("--chat-model", default=None)
    parser.add_argument("--embedding-model", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    store = provision_memory_store(
        name=args.name,
        ttl_days=args.ttl_days,
        chat_model=args.chat_model,
        embedding_model=args.embedding_model,
    )
    print(f"Provisioned memory store: {getattr(store, 'name', args.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
