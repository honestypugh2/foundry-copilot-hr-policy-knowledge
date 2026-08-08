"""Regression tests for the shared KB and Pattern B provisioning payloads."""

from src.agents.create_foundry_agent import (
    _build_knowledge_base,
    _build_prompt_agent_definition,
)


def test_shared_kb_is_medium_extractive_without_answer_synthesis(monkeypatch):
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1"
    )

    payload = _build_knowledge_base().as_dict()

    assert payload["models"][0]["azureOpenAIParameters"] == {
        "resourceUri": "https://example.openai.azure.com",
        "deploymentId": "gpt-5-mini",
        "modelName": "gpt-5-mini",
    }
    assert payload["retrievalReasoningEffort"] == {"kind": "medium"}
    assert payload["outputMode"] == "extractiveData"
    assert payload["retrievalInstructions"]
    assert "answerInstructions" not in payload


def test_pattern_b_requires_the_knowledge_base_tool():
    payload = _build_prompt_agent_definition(
        "https://example.search.windows.net/knowledgebases/hr-knowledge-base/mcp"
    ).as_dict()

    assert payload["tool_choice"] == "required"
    assert payload["tools"][0]["allowed_tools"] == ["knowledge_base_retrieve"]
    assert payload["tools"][0]["require_approval"] == "never"