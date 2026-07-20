"""Unit tests for the Foundry memory store builders (P2.7)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from src.memory import memory_store as ms


pytestmark = pytest.mark.skipif(
    not ms.MEMORY_SDK_AVAILABLE, reason="azure-ai-projects not installed"
)


def test_build_memory_options_sets_all_fields_and_ttl_timedelta():
    options = ms.build_memory_options(ttl_days=30)
    assert options.user_profile_enabled is True
    assert options.chat_summary_enabled is True
    assert options.procedural_memory_enabled is True
    # TTL is a timedelta in azure-ai-projects 2.3.0.
    assert options.default_ttl_seconds == timedelta(days=30)


def test_build_memory_options_respects_overrides():
    options = ms.build_memory_options(
        ttl_days=7,
        procedural_memory_enabled=False,
        user_profile_enabled=False,
    )
    assert options.procedural_memory_enabled is False
    assert options.user_profile_enabled is False
    assert options.chat_summary_enabled is True
    assert options.default_ttl_seconds == timedelta(days=7)


def test_build_memory_definition_uses_model_policy(monkeypatch):
    monkeypatch.setenv("FOUNDRY_MODEL", "gpt-5")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    definition = ms.build_memory_definition()
    assert definition.chat_model == "gpt-5"
    assert definition.embedding_model == "text-embedding-3-large"
    assert definition.options is not None


def test_build_memory_definition_default_models(monkeypatch):
    for var in ("FOUNDRY_MODEL", "AZURE_OPENAI_DEPLOYMENT_NAME", "AZURE_OPENAI_DEPLOYMENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", raising=False)
    definition = ms.build_memory_definition()
    assert definition.chat_model == "gpt-5-mini"
    assert definition.embedding_model == "text-embedding-3-small"
