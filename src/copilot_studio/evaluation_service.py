"""Supported Power Platform API client for Copilot Studio maker evaluations."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic, sleep
from typing import Any

import httpx

from src.config.azure_identity import _token_claims


class CopilotStudioEvaluationService:
    """Trigger an existing test set and retrieve its native evaluation results."""

    API_VERSION = "2024-10-01"
    TERMINAL_STATES = {"Abandoned", "Cancelled", "Completed", "Deleted", "Failed"}

    def __init__(
        self,
        *,
        environment_id: str,
        bot_id: str,
        credential: Any,
        expected_tenant_id: str,
        expected_principal_id: str,
        client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        required = {
            "environment_id": environment_id,
            "bot_id": bot_id,
            "expected_tenant_id": expected_tenant_id,
            "expected_principal_id": expected_principal_id,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(
                "Missing Copilot Studio evaluation settings: " + ", ".join(missing)
            )
        self.environment_id = environment_id
        self.bot_id = bot_id
        self._credential = credential
        self._expected_tenant_id = expected_tenant_id.lower()
        self._expected_principal_id = expected_principal_id.lower()
        self._client = client or httpx.Client(timeout=30)
        self._sleep = sleep_fn

    @property
    def _base_url(self) -> str:
        return (
            "https://api.powerplatform.com/copilotstudio/environments/"
            f"{self.environment_id}/bots/{self.bot_id}/api/makerevaluation"
        )

    def _authorization_header(self) -> dict[str, str]:
        token = self._credential.get_token(
            "https://api.powerplatform.com/.default"
        ).token
        claims = _token_claims(token)
        actual_tenant = str(claims.get("tid") or "").lower()
        actual_principal = str(claims.get("oid") or "").lower()
        if actual_tenant != self._expected_tenant_id:
            raise RuntimeError(
                "Power Platform token tenant does not match the pinned Azure tenant"
            )
        if actual_principal != self._expected_principal_id:
            raise RuntimeError(
                "Power Platform token principal does not match the pinned Azure principal"
            )
        return {"Authorization": f"Bearer {token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(
            method,
            f"{self._base_url}/{path}",
            params={"api-version": self.API_VERSION},
            headers=self._authorization_header(),
            **kwargs,
        )
        if response.status_code == 403:
            raise PermissionError(
                "Power Platform API denied the evaluation request. Use an app "
                "registration with the required delegated Copilot Studio maker "
                "permissions and tenant admin consent."
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Copilot Studio Evaluation API returned a non-object")
        return payload

    def list_test_sets(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "testsets")
        values = payload.get("value")
        if not isinstance(values, list):
            raise ValueError("Test-set response is missing the value list")
        return [item for item in values if isinstance(item, dict)]

    def resolve_test_set(
        self, display_name: str, *, expected_case_count: int
    ) -> dict[str, Any]:
        matches = [
            item
            for item in self.list_test_sets()
            if item.get("displayName") == display_name
            and item.get("state") == "Active"
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one active Copilot Studio test set named {display_name!r}; "
                f"found {len(matches)}"
            )
        test_set = matches[0]
        if test_set.get("totalTestCases") != expected_case_count:
            raise ValueError(
                f"Test set {display_name!r} has {test_set.get('totalTestCases')} "
                f"cases; expected {expected_case_count}"
            )
        return test_set

    def start_run(
        self,
        test_set_id: str,
        *,
        run_name: str,
        run_on_published_bot: bool = True,
        mcs_connection_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "evaluationRunName": run_name,
            "runOnPublishedBot": run_on_published_bot,
            "toolsConnections": [],
        }
        if mcs_connection_id:
            body["mcsConnectionId"] = mcs_connection_id
        return self._request("POST", f"testsets/{test_set_id}/run", json=body)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"testruns/{run_id}")

    def wait_for_run(
        self,
        run_id: str,
        *,
        timeout_seconds: float = 900,
        poll_interval_seconds: float = 5,
    ) -> dict[str, Any]:
        deadline = monotonic() + timeout_seconds
        while True:
            run = self.get_run(run_id)
            state = str(run.get("state") or "Unknown")
            if state in self.TERMINAL_STATES:
                if state != "Completed":
                    raise RuntimeError(
                        f"Copilot Studio evaluation {run_id} ended in state {state}"
                    )
                return run
            if monotonic() >= deadline:
                raise TimeoutError(
                    f"Copilot Studio evaluation {run_id} did not finish in time"
                )
            self._sleep(poll_interval_seconds)

    def run_named_test_set(
        self,
        *,
        test_set_name: str,
        expected_case_count: int,
        run_name: str,
        run_on_published_bot: bool = True,
        mcs_connection_id: str | None = None,
        timeout_seconds: float = 900,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        test_set = self.resolve_test_set(
            test_set_name, expected_case_count=expected_case_count
        )
        status = self.start_run(
            str(test_set["id"]),
            run_name=run_name,
            run_on_published_bot=run_on_published_bot,
            mcs_connection_id=mcs_connection_id,
        )
        run_id = str(status.get("runId") or "")
        if not run_id:
            raise ValueError("Evaluation start response is missing runId")
        return test_set, self.wait_for_run(
            run_id,
            timeout_seconds=timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()