"""Default smoke tests against the deployed non-production Azure environment."""

from __future__ import annotations

import asyncio
import io
import os
import subprocess

import httpx
import pytest
from azure.identity import AzureCliCredential
from dotenv import dotenv_values, load_dotenv

from src.search.integrated_vectorization_search import (
    IntegratedVectorizationSearchService,
)


load_dotenv()
pytestmark = pytest.mark.live


@pytest.fixture(scope="module", autouse=True)
def _load_live_azure_environment() -> None:
    result = subprocess.run(
        ["azd", "env", "get-values", "--environment", "hr-demo"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "Live Azure tests require the authenticated azd environment 'hr-demo': "
            f"{result.stderr.strip()}"
        )
    for name, value in dotenv_values(stream=io.StringIO(result.stdout)).items():
        if value:
            os.environ.setdefault(name, value)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip().strip('"')
    if not value:
        pytest.fail(f"{name} is required for live Azure tests")
    return value


def _management_headers() -> dict[str, str]:
    token = AzureCliCredential().get_token(
        "https://management.azure.com/.default"
    )
    return {"Authorization": f"Bearer {token.token}"}


@pytest.mark.asyncio
async def test_live_search_returns_part_time_pto_policy():
    service = IntegratedVectorizationSearchService()
    assert service.is_configured

    hits = await asyncio.to_thread(service.search, "part-time PTO policy", 5)

    matching = [hit for hit in hits if hit.get("policy_number") == "50020"]
    assert matching, "Live Search did not return Policy 50020 in the top five hits"
    assert "part-time" in matching[0]["title"].lower()
    assert matching[0]["blob_url"].startswith("https://")


@pytest.mark.asyncio
async def test_live_pattern_c_backend_health_and_lookup():
    backend_uri = _required_env("SERVICE_BACKEND_URI").rstrip("/")
    async with httpx.AsyncClient(timeout=60) as client:
        health = await client.get(f"{backend_uri}/api/health")
        lookup = await client.post(
            f"{backend_uri}/api/lookup",
            json={"query": "part-time PTO policy"},
        )

    health.raise_for_status()
    lookup.raise_for_status()
    assert health.json()["status"] == "healthy"
    payload = lookup.json()
    assert payload["policy_id"] == "50020"
    assert payload["blob_url"].startswith("https://")
    assert payload["documents"][0]["policy_number"] == "50020"


@pytest.mark.asyncio
async def test_live_grafana_and_load_testing_resources_are_ready():
    subscription_id = _required_env("AZURE_SUBSCRIPTION_ID")
    resource_group = _required_env("AZURE_RESOURCE_GROUP")
    grafana_name = _required_env("AZURE_MANAGED_GRAFANA_NAME")
    load_testing_name = _required_env("AZURE_LOAD_TESTING_NAME")
    root = (
        "https://management.azure.com/subscriptions/"
        f"{subscription_id}/resourceGroups/{resource_group}/providers"
    )
    targets = (
        (
            "grafana",
            f"{root}/Microsoft.Dashboard/grafana/{grafana_name}",
            "2024-10-01",
        ),
        (
            "load_testing",
            f"{root}/Microsoft.LoadTestService/loadTests/{load_testing_name}",
            "2022-12-01",
        ),
    )

    async with httpx.AsyncClient(timeout=60, headers=_management_headers()) as client:
        resources = {}
        for label, url, api_version in targets:
            response = await client.get(url, params={"api-version": api_version})
            response.raise_for_status()
            resources[label] = response.json()

    assert resources["grafana"]["properties"]["provisioningState"] == "Succeeded"
    assert resources["grafana"]["properties"]["endpoint"].startswith("https://")
    assert resources["grafana"]["identity"]["principalId"]
    assert resources["load_testing"]["properties"]["provisioningState"] == "Succeeded"
    assert resources["load_testing"]["properties"]["dataPlaneURI"].endswith(
        ".loadtesting.azure.com"
    )