import asyncio

import pytest

from src.copilot_studio.service import CopilotStudioService


def test_copilot_studio_requires_published_mobile_token_endpoint(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")
    monkeypatch.delenv("COPILOT_STUDIO_TOKEN_ENDPOINT", raising=False)

    service = CopilotStudioService(
        environment_id="Default-tenant-id",
        agent_schema="Default_AskHRPolicyAgent",
    )

    assert service.is_configured is False
    assert service.get_config()["token_endpoint_url"] is None
    with pytest.raises(RuntimeError, match="Channels > Mobile app"):
        _ = service.token_endpoint_url


def test_copilot_studio_uses_exact_mobile_token_endpoint(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")
    token_endpoint = (
        "https://defaulttenant.d7.environment.api.powerplatform.com/"
        "powervirtualagents/botsbyschema/Default_AskHRPolicyAgent/directline/token"
    )

    service = CopilotStudioService(
        environment_id="Default-tenant-id",
        agent_schema="Default_AskHRPolicyAgent",
        token_endpoint=token_endpoint,
    )

    assert service.is_configured is True
    assert service.token_endpoint_url == token_endpoint
    assert service.get_config()["token_endpoint_url"] == token_endpoint


def test_copilot_studio_rejects_token_endpoint_for_another_agent(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")
    token_endpoint = (
        "https://defaulttenant.d7.environment.api.powerplatform.com/"
        "powervirtualagents/botsbyschema/Default_OtherAgent/directline/token"
    )

    with pytest.raises(ValueError, match="agent schema does not match"):
        CopilotStudioService(
            environment_id="Default-tenant-id",
            agent_schema="Default_AskHRPolicyAgent",
            token_endpoint=token_endpoint,
        )


@pytest.mark.asyncio
async def test_send_message_ignores_channel_rewritten_user_activity(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"id": "posted-user-activity"})

        async def get(self, *_args, **_kwargs):
            return FakeResponse(
                {
                    "watermark": "1",
                    "activities": [
                        {
                            "id": "posted-user-activity",
                            "type": "message",
                            "from": {"id": "channel-rewritten-user-id"},
                            "text": "Give me the part-time PTO policy.",
                        },
                        {
                            "id": "bot-activity",
                            "type": "message",
                            "from": {"id": "bot", "role": "bot"},
                            "text": "Policy 50020",
                        },
                    ],
                }
            )

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("src.copilot_studio.service.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    service = CopilotStudioService(
        environment_id="Default-tenant-id",
        agent_schema="Default_AskHRPolicyAgent",
        token_endpoint="https://example.test/directline/token",
    )

    result = await service.send_message(
        conversation_id="conversation-1",
        token="token",
        message="Give me the part-time PTO policy.",
    )

    assert result["answer"] == "Policy 50020"
    assert [activity["id"] for activity in result["activities"]] == ["bot-activity"]
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_send_message_waits_beyond_twenty_polls(monkeypatch):
    monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, **_kwargs):
            self.polls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"id": "posted-user-activity"})

        async def get(self, *_args, **_kwargs):
            self.polls += 1
            activities = []
            if self.polls == 21:
                activities = [
                    {
                        "id": "bot-activity",
                        "type": "message",
                        "from": {"id": "bot", "role": "bot"},
                        "text": "Policies 50010 and 50020",
                    }
                ]
            return FakeResponse(
                {"watermark": str(self.polls), "activities": activities}
            )

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("src.copilot_studio.service.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    service = CopilotStudioService(
        environment_id="Default-tenant-id",
        agent_schema="Default_AskHRPolicyAgentB",
        token_endpoint="https://example.test/directline/token",
    )

    result = await service.send_message(
        conversation_id="conversation-1",
        token="token",
        message="Compare full-time and part-time PTO.",
    )

    assert result["answer"] == "Policies 50010 and 50020"
    assert result["timed_out"] is False