"""
HR Policy Agent — Foundry Agent Service (Prompt Agent + MCP)

Pattern B: Foundry Agent Service (agentic retrieval).

Uses ``azure-ai-projects>=2.2.0`` to publish a `PromptAgentDefinition` whose
only tool is an `MCPTool` pointing at the Azure AI Search Knowledge Base
MCP endpoint. With ``tool_choice="required"`` the agent always grounds
answers in the knowledge base before responding.

Provisioning of the Knowledge Source / Knowledge Base / MCP connection is
handled by ``src/agents/create_foundry_agent.py``.

Quickstart reference:
    https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent?tabs=python
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Optional

from src.config.search_config import search_cfg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Foundry SDK imports (optional — fallback path runs without them)
# ---------------------------------------------------------------------------
try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import MCPTool, PromptAgentDefinition
    from azure.identity import DefaultAzureCredential

    FOUNDRY_SDK_AVAILABLE = True
except ImportError:
    FOUNDRY_SDK_AVAILABLE = False
    AIProjectClient = None  # type: ignore[assignment,misc]
    MCPTool = None  # type: ignore[assignment,misc]
    PromptAgentDefinition = None  # type: ignore[assignment,misc]
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    logger.warning(
        "azure-ai-projects / azure-identity not installed; Foundry Agent Service "
        "path unavailable — falling back to local search."
    )


# Local search service for the no-Foundry fallback path.
from src.search.search_service import HRPolicySearchService, expand_query_with_glossary
from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService


# ---------------------------------------------------------------------------
# Agent configuration (shared with orchestrator.py)
# ---------------------------------------------------------------------------
AGENT_NAME = "HRPolicyAgent"

AGENT_INSTRUCTIONS = """You are an HR Policy Assistant for the "Ask HR" system.
Your role is to answer employee questions based on INTERNAL HR policy documents ONLY.

CRITICAL RULES:
1. Only answer based on the HR policy documents retrieved from the knowledge base.
2. If information is not found in the policy documents, say "I could not find this information in the HR policy documents. Please contact your HR representative for assistance."
3. Always cite the specific policy number and title when referencing information.
4. Be precise with policy details - do not paraphrase in ways that change meaning.
5. If a question is ambiguous, ask for clarification.
6. Handle vernacular/shorthand terms by mapping to formal policy names (e.g., "PTO" -> "Paid Time Off", "dress code" -> "Uniform Dress Code").
7. Format responses clearly with policy references.

RESPONSE FORMAT:
- Start with a direct answer to the question
- Include specific policy citations: [Policy XXXXX - Title]
- Quote relevant sections when precision matters
- End with "Source: [Policy Number - Policy Title]" for each referenced policy
"""


# ---------------------------------------------------------------------------
# Helpers — Knowledge Base MCP endpoint
# ---------------------------------------------------------------------------
def _build_kb_mcp_endpoint() -> str:
    """Resolve the MCP endpoint URL for the HR knowledge base.

    Format:
        ``{search_endpoint}/knowledgebases/{kb_name}/mcp?api-version={api_version}``
    """
    search_endpoint = (os.getenv("AZURE_SEARCH_ENDPOINT") or "").rstrip("/")
    kb_name = search_cfg.knowledge_base_name
    api_version = search_cfg.agentic_retrieval.get("mcp", {}).get(
        "api_version", "2025-11-01-Preview"
    )
    if not search_endpoint:
        return ""
    return f"{search_endpoint}/knowledgebases/{kb_name}/mcp?api-version={api_version}"


def _resolve_credential() -> Any:
    """Return a sync credential, preferring CLI for local dev."""
    try:
        from azure.identity import AzureCliCredential

        return AzureCliCredential(process_timeout=30)
    except Exception:
        return DefaultAzureCredential() if DefaultAzureCredential else None


# ---------------------------------------------------------------------------
# HRPolicyAgent — Foundry Agent Service (PromptAgent + MCP)
# ---------------------------------------------------------------------------
class HRPolicyAgent:
    """Foundry Agent Service prompt agent backed by an Azure AI Search Knowledge Base.

    Public API mirrors ``hr_policy_agent_af.HRPolicyAgent`` so the orchestrator
    can swap implementations via ``AGENT_SERVICE``.
    """

    def __init__(
        self,
        use_agent: bool = True,
        project_endpoint: Optional[str] = None,
        model_deployment_name: Optional[str] = None,
        search_mode: Optional[str] = None,
    ):
        self.use_agent = use_agent and FOUNDRY_SDK_AVAILABLE
        self.project_endpoint = (
            project_endpoint
            or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
            or os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
        )
        self.model_deployment_name = (
            model_deployment_name
            or os.getenv("FOUNDRY_MODEL")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        )
        self.search_mode = search_mode or os.getenv("SEARCH_MODE", "integrated_vectorization")

        # Lazily initialised clients / state
        self._project: Any = None
        self._openai: Any = None
        self._agent_version: Optional[str] = None
        self._initialized = False

        # Local search service (fallback when Foundry isn't configured)
        self._search_service: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @property
    def search_service(self) -> Any:
        if self._search_service is None:
            if self.search_mode == "integrated_vectorization":
                self._search_service = IntegratedVectorizationSearchService()
            else:
                self._search_service = HRPolicySearchService()
        return self._search_service

    async def initialize(self) -> None:
        """Ensure the prompt agent exists in the Foundry project (idempotent)."""
        if self._initialized:
            return

        if not self.use_agent or not self.project_endpoint:
            logger.info(
                "Foundry Agent Service disabled (use_agent=%s, project_endpoint=%s); "
                "using local search fallback.",
                self.use_agent,
                bool(self.project_endpoint),
            )
            self._initialized = True
            return

        if not FOUNDRY_SDK_AVAILABLE:
            logger.warning("azure-ai-projects not installed; falling back to local search")
            self._initialized = True
            return

        try:
            credential = _resolve_credential()
            self._project = AIProjectClient(  # type: ignore[misc]
                endpoint=self.project_endpoint,
                credential=credential,
            )

            self._ensure_prompt_agent()
            self._openai = self._project.get_openai_client()

            logger.info(
                "Foundry prompt agent '%s' ready (model=%s)",
                AGENT_NAME,
                self.model_deployment_name,
            )
        except Exception as e:
            logger.error("Failed to initialize Foundry prompt agent: %s", e)
            self._project = None
            self._openai = None
        finally:
            self._initialized = True

    def _ensure_prompt_agent(self) -> None:
        """Create or update the PromptAgentDefinition with an MCPTool."""
        try:
            existing = self._project.agents.get(agent_name=AGENT_NAME)
            self._agent_version = getattr(existing, "version", None)
            logger.info("Found existing prompt agent '%s' (version %s)", AGENT_NAME, self._agent_version)
            return
        except Exception:
            logger.info("Prompt agent '%s' not found; creating new version", AGENT_NAME)

        mcp_endpoint = _build_kb_mcp_endpoint()
        if not mcp_endpoint:
            logger.warning(
                "AZURE_SEARCH_ENDPOINT not set; creating prompt agent without MCP tool. "
                "Run src/agents/create_foundry_agent.py to provision the knowledge base."
            )
            tools: list[Any] = []
            tool_choice: Any = "auto"
        else:
            mcp_connection_name = search_cfg.mcp_connection_name
            tools = [
                MCPTool(  # type: ignore[misc]
                    server_label="hr-knowledge",
                    server_url=mcp_endpoint,
                    require_approval="never",
                    allowed_tools=["knowledge_base_retrieve"],
                    project_connection_id=mcp_connection_name,
                )
            ]
            # Force the agent to call the knowledge base on every turn.
            tool_choice = "required"

        agent = self._project.agents.create_version(
            agent_name=AGENT_NAME,
            definition=PromptAgentDefinition(  # type: ignore[misc]
                model=self.model_deployment_name,
                instructions=AGENT_INSTRUCTIONS,
                tools=tools,
                tool_choice=tool_choice,
            ),
        )
        self._agent_version = getattr(agent, "version", None)
        logger.info(
            "Created prompt agent '%s' version %s with %d tool(s)",
            AGENT_NAME,
            self._agent_version,
            len(tools),
        )

    async def close(self) -> None:
        """Release local resources. The prompt agent remains in the portal."""
        self._project = None
        self._openai = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Answer flow
    # ------------------------------------------------------------------
    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        if self.use_agent and self.project_endpoint:
            return await self._agent_answer(question, conversation_history)
        return await self._local_answer(question)

    async def _agent_answer(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        if not self._initialized:
            await self.initialize()

        if not self._openai:
            logger.warning("Foundry client unavailable; using local search fallback")
            return await self._local_answer(question)

        try:
            return await asyncio.to_thread(
                self._invoke_responses_api, question, conversation_history
            )
        except Exception as e:
            logger.error("Foundry prompt agent invocation failed: %s", e)
            return await self._local_answer(question)

    def _invoke_responses_api(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Synchronous Responses API call (used from a worker thread)."""
        prompt = self._build_prompt(question, conversation_history)
        conversation = self._openai.conversations.create()

        response = self._openai.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
            input=prompt,
        )

        answer = getattr(response, "output_text", "") or ""
        if not answer:
            # Fall back to extracting from response.output if output_text is missing.
            for item in getattr(response, "output", []) or []:
                for block in getattr(item, "content", []) or []:
                    text = getattr(block, "text", None)
                    if text:
                        answer = text
                        break
                if answer:
                    break

        return self._parse_agent_response(answer or "The agent did not produce a response.", question)

    # ------------------------------------------------------------------
    # Local fallback
    # ------------------------------------------------------------------
    async def _local_answer(self, question: str) -> dict[str, Any]:
        """No-LLM fallback: return raw search results with citations."""
        results = self.search_service.search(question, top=3)

        if not results:
            return {
                "answer": (
                    "I could not find relevant HR policy information for your question. "
                    "Please contact your HR representative for assistance."
                ),
                "citations": [],
                "confidence": 0.0,
                "policy_references": [],
            }

        answer_parts = ["Based on the HR policy documents, here is what I found:\n"]
        citations: list[dict[str, Any]] = []
        policy_refs: list[str] = []

        for i, result in enumerate(results, 1):
            title = result.get("title", result.get("parent_title", "Unknown Policy"))
            policy_num = result.get("policy_number", "")
            content = result.get("content", "")[:500]

            answer_parts.append(f"**{i}. {title}** (Policy {policy_num})")
            answer_parts.append(f"{content}\n")

            citations.append(
                {"title": title, "policy_number": policy_num, "excerpt": content[:200]}
            )
            if policy_num:
                policy_refs.append(f"Policy {policy_num} - {title}")

        answer_parts.append(
            "\n*Note: This response is based on search results without AI summarization. "
            "Configure AZURE_AI_PROJECT_ENDPOINT to enable Foundry Agent Service.*"
        )

        return {
            "answer": "\n".join(answer_parts),
            "citations": citations,
            "confidence": min(results[0].get("score", 0) / 10.0, 1.0) if results else 0.0,
            "policy_references": policy_refs,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        parts: list[str] = []
        if conversation_history:
            parts.append("Previous conversation context:")
            for msg in conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role}: {content}")
            parts.append("")

        expanded = expand_query_with_glossary(question)
        parts.append(f"Employee Question: {expanded}")
        return "\n".join(parts)

    def _parse_agent_response(self, response_text: str, original_question: str) -> dict[str, Any]:
        citations: list[dict[str, Any]] = []
        policy_refs: list[str] = []

        policy_pattern = r"\[?Policy\s+(\d+)\s*[-\u2013]\s*([^\]]+)\]?"
        for num, title in re.findall(policy_pattern, response_text, re.IGNORECASE):
            citations.append({"policy_number": num, "title": title.strip()})
            policy_refs.append(f"Policy {num} - {title.strip()}")

        return {
            "answer": response_text,
            "citations": citations,
            "confidence": 0.85 if citations else 0.6,
            "policy_references": list(set(policy_refs)),
        }

    def answer_question(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Synchronous wrapper for ``answer_question_async``."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_question_async(question, conversation_history))
        future = asyncio.ensure_future(
            self.answer_question_async(question, conversation_history),
            loop=loop,
        )
        return loop.run_until_complete(future)
