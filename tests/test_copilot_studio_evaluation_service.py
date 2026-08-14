from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import httpx
import pytest

from src.copilot_studio.evaluation_service import CopilotStudioEvaluationService


def _token(tenant: str = "tenant-1", principal: str = "principal-1") -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"tid": tenant, "oid": principal}).encode()
    ).decode().rstrip("=")
    return f"header.{payload}.signature"


class FakeCredential:
    def __init__(self, token: str | None = None):
        self.token = token or _token()

    def get_token(self, _scope: str):
        return SimpleNamespace(token=self.token)


def _service(handler):
    return CopilotStudioEvaluationService(
        environment_id="environment-1",
        bot_id="bot-1",
        credential=FakeCredential(),
        expected_tenant_id="tenant-1",
        expected_principal_id="principal-1",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep_fn=lambda _seconds: None,
    )


def test_runs_exact_active_test_set_and_polls_to_completion():
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        if request.url.path.endswith("/testsets"):
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "set-1",
                            "displayName": "Ask HR Pattern A release-v1",
                            "state": "Active",
                            "totalTestCases": 9,
                        }
                    ]
                },
            )
        if request.method == "POST":
            return httpx.Response(200, json={"runId": "run-1", "state": "Queued"})
        return httpx.Response(
            200,
            json={
                "id": "run-1",
                "testSetId": "set-1",
                "state": "Completed",
                "totalTestCases": 9,
                "testCasesResults": [],
            },
        )

    service = _service(handler)
    test_set, run = service.run_named_test_set(
        test_set_name="Ask HR Pattern A release-v1",
        expected_case_count=9,
        run_name="benchmark-20260811",
    )

    assert test_set["id"] == "set-1"
    assert run["state"] == "Completed"
    post_body = json.loads(next(item for item in requests if item.method == "POST").content)
    assert post_body["runOnPublishedBot"] is True
    assert post_body["evaluationRunName"] == "benchmark-20260811"


def test_rejects_test_set_with_wrong_case_count():
    def handler(_request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "set-1",
                        "displayName": "release-v1",
                        "state": "Active",
                        "totalTestCases": 7,
                    }
                ]
            },
        )

    with pytest.raises(ValueError, match="has 7 cases; expected 9"):
        _service(handler).resolve_test_set("release-v1", expected_case_count=9)


def test_rejects_power_platform_token_for_wrong_identity():
    service = CopilotStudioEvaluationService(
        environment_id="environment-1",
        bot_id="bot-1",
        credential=FakeCredential(_token(tenant="other-tenant")),
        expected_tenant_id="tenant-1",
        expected_principal_id="principal-1",
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))),
    )

    with pytest.raises(RuntimeError, match="token tenant"):
        service.list_test_sets()


def test_reports_delegated_permission_failure_without_response_body():
    service = _service(lambda _request: httpx.Response(403, json={"error": "details"}))

    with pytest.raises(PermissionError, match="delegated Copilot Studio"):
        service.list_test_sets()