"""
Copilot Studio Service — Direct-to-Engine API Client

Provides two integration modes:
1. **Token mode** — Fetches a Direct Line token so the React frontend can
   embed the Copilot Studio Web Chat widget and talk to the agent directly.
2. **Proxy mode** — Backend-to-bot conversation using the Direct-to-Engine
   REST API, useful for server-side orchestration or testing.

References:
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-bot-authentication
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/publication-connect-bot-to-custom-application
- https://github.com/Azure-Samples/Copilot-Studio-with-Azure-AI-Search
"""

import logging
import os
from typing import Any, Optional

import httpx
from azure.identity import (
    AzureCliCredential,
    ManagedIdentityCredential,
    ChainedTokenCredential,
)

logger = logging.getLogger(__name__)


class CopilotStudioService:
    """
    Client for the Copilot Studio Direct-to-Engine API.

    Environment variables consumed:
        COPILOT_STUDIO_ENVIRONMENT_ID   Power Platform environment ID
        COPILOT_STUDIO_AGENT_SCHEMA     Agent schema name (e.g. crf6d_askHrAgent)
        COPILOT_STUDIO_TOKEN_ENDPOINT   Full token endpoint URL (overrides auto-build)
        COPILOT_STUDIO_ENDPOINT         API base URL (default: https://api.copilotstudio.microsoft.com)
        COPILOT_STUDIO_REGION           Region prefix for token URL (e.g. unitedstates)
    """

    def __init__(self):
        self.environment_id = os.getenv("COPILOT_STUDIO_ENVIRONMENT_ID", "")
        self.agent_schema = os.getenv("COPILOT_STUDIO_AGENT_SCHEMA", "")
        self.endpoint = os.getenv(
            "COPILOT_STUDIO_ENDPOINT",
            "https://api.copilotstudio.microsoft.com",
        )
        self.region = os.getenv("COPILOT_STUDIO_REGION", "unitedstates")

        # Allow full override of the token endpoint
        self._token_endpoint_override = os.getenv("COPILOT_STUDIO_TOKEN_ENDPOINT", "")

        # Build credential chain for Entra ID auth
        use_managed = os.getenv("USE_MANAGED_IDENTITY", "true").lower() == "true"
        if use_managed:
            self._credential = ChainedTokenCredential(
                ManagedIdentityCredential(),
                AzureCliCredential(),
            )
        else:
            self._credential = AzureCliCredential()

    # ------------------------------------------------------------------ #
    #  Configuration helpers                                               #
    # ------------------------------------------------------------------ #

    @property
    def is_configured(self) -> bool:
        return bool(self.environment_id and self.agent_schema)

    @property
    def token_endpoint_url(self) -> str:
        """
        Build the Direct Line token endpoint URL.

        Format:
        https://<region>.api.powerplatform.com/copilotstudio/
          environments/<env_id>/agents/<schema>/directline/token
          ?api-version=2022-03-01-preview
        """
        if self._token_endpoint_override:
            return self._token_endpoint_override

        return (
            f"https://{self.region}.api.powerplatform.com"
            f"/copilotstudio/environments/{self.environment_id}"
            f"/agents/{self.agent_schema}"
            f"/directline/token?api-version=2022-03-01-preview"
        )

    def get_config(self) -> dict[str, Any]:
        """Public configuration (safe to expose to the frontend)."""
        return {
            "environment_id": self.environment_id,
            "agent_schema": self.agent_schema,
            "region": self.region,
            "is_configured": self.is_configured,
            "token_endpoint_url": self.token_endpoint_url if self.is_configured else None,
        }

    # ------------------------------------------------------------------ #
    #  Token endpoint — called by the frontend to embed Web Chat         #
    # ------------------------------------------------------------------ #

    async def get_directline_token(self) -> dict[str, Any]:
        """
        Fetch a Direct Line token from the Copilot Studio token endpoint.

        Returns dict with:
          - token: str
          - conversationId: str (optional)
          - expires_in: int (seconds)
        """
        if not self.is_configured:
            raise RuntimeError(
                "Copilot Studio is not configured. "
                "Set COPILOT_STUDIO_ENVIRONMENT_ID and COPILOT_STUDIO_AGENT_SCHEMA."
            )

        url = self.token_endpoint_url
        logger.info(f"Requesting Direct Line token from {url}")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        logger.info("Direct Line token acquired")
        return {
            "token": data.get("token", ""),
            "conversationId": data.get("conversationId", ""),
            "expires_in": data.get("expires_in", 900),
        }

    # ------------------------------------------------------------------ #
    #  Direct-to-Engine proxy — backend-side conversation                 #
    # ------------------------------------------------------------------ #

    async def start_conversation(self) -> dict[str, Any]:
        """Start a new conversation via Direct Line."""
        token_data = await self.get_directline_token()
        token = token_data["token"]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://directline.botframework.com/v3/directline/conversations",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def send_message(
        self,
        conversation_id: str,
        token: str,
        message: str,
    ) -> dict[str, Any]:
        """Send a message to an active conversation and return the response."""
        url = (
            f"https://directline.botframework.com/v3/directline"
            f"/conversations/{conversation_id}/activities"
        )

        payload = {
            "type": "message",
            "from": {"id": "user"},
            "text": message,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            # Post the user message
            post_resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            post_resp.raise_for_status()
            activity_id = post_resp.json().get("id", "")

            # Poll for bot response
            bot_responses: list[dict] = []
            watermark: Optional[str] = None
            max_polls = 20

            for _ in range(max_polls):
                import asyncio
                await asyncio.sleep(1)

                params: dict[str, str] = {}
                if watermark:
                    params["watermark"] = watermark

                get_resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                get_resp.raise_for_status()
                data = get_resp.json()
                watermark = data.get("watermark")

                for activity in data.get("activities", []):
                    if (
                        activity.get("from", {}).get("id") != "user"
                        and activity.get("type") == "message"
                        and activity.get("text")
                    ):
                        bot_responses.append(activity)

                if bot_responses:
                    break

        # Combine all bot response parts
        combined_text = " ".join(a.get("text", "") for a in bot_responses)
        return {
            "answer": combined_text,
            "activities": bot_responses,
            "activity_id": activity_id,
        }
