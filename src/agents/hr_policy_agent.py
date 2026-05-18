"""
HR Policy Agent

RAG-based agent that answers employee questions using Azure AI Search
to retrieve relevant HR policy documents and Azure OpenAI for generation.

Uses Agent Framework ``FoundryChatClient`` with ``@tool``-decorated search
functions for grounded, citation-backed responses.

References:
    Agent Framework overview:
        https://learn.microsoft.com/en-us/agent-framework/overview/
    Add tools:
        https://learn.microsoft.com/en-us/agent-framework/get-started/add-tools
    FoundryChatClient (Foundry provider):
        https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry
"""

from __future__ import annotations

import logging
import os
import re
from typing import Annotated, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent Framework imports
# ---------------------------------------------------------------------------
try:
    from agent_framework import Agent, tool
    from agent_framework.foundry import FoundryChatClient
    from azure.identity import DefaultAzureCredential
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    Agent = None  # type: ignore[assignment,misc]  # noqa: N806
    FoundryChatClient = None  # type: ignore[assignment,misc]  # noqa: N806
    DefaultAzureCredential = None  # type: ignore[assignment,misc]  # noqa: N806
    logger.warning("agent-framework or azure-identity not installed, agent mode unavailable")

from src.search.search_service import HRPolicySearchService, expand_query_with_glossary
from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------
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
# Tools — defined at module level so they can be passed to Agent(tools=[...])
# ---------------------------------------------------------------------------

# A module-level search service instance is needed by the tool functions.
# Lazily initialised on first use.
_search_service: Optional[Any] = None


def _get_search_service() -> Any:
    global _search_service
    if _search_service is None:
        mode = os.getenv("SEARCH_MODE", "integrated_vectorization")
        if mode == "integrated_vectorization":
            _search_service = IntegratedVectorizationSearchService()
        else:
            _search_service = HRPolicySearchService()
    return _search_service


@tool(approval_mode="never_require")
def search_hr_policies(
    query: Annotated[str, "The employee's HR question to search for in the knowledge base"],
) -> str:
    """Search the HR policy knowledge base and return relevant policy excerpts.

    Expands the query with HR glossary terms (e.g. PTO → Paid Time Off) before
    searching with hybrid vector + semantic ranking.
    """
    expanded = expand_query_with_glossary(query)
    svc = _get_search_service()
    results = svc.search(expanded, top=5)

    if not results:
        return "No relevant HR policy documents found for this query."

    parts = []
    for i, result in enumerate(results, 1):
        title = result.get("title", result.get("parent_title", "Unknown Policy"))
        policy_num = result.get("policy_number", "")
        content = result.get("content", "")[:800]
        parts.append(f"[{i}] Policy {policy_num} - {title}\n{content}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# HRPolicyAgent
# ---------------------------------------------------------------------------

class HRPolicyAgent:
    """
    HR Policy Agent using Agent Framework + FoundryChatClient.

    Modes:
    1. FoundryChatClient Agent with ``search_hr_policies`` tool — full RAG
    2. Local search fallback (no LLM) when Foundry is not configured
    """

    def __init__(
        self,
        use_agent: bool = True,
        project_endpoint: Optional[str] = None,
        model_deployment_name: Optional[str] = None,
        search_mode: Optional[str] = None,
    ):
        self.use_agent = use_agent and AGENT_FRAMEWORK_AVAILABLE
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

        # Search mode: "integrated_vectorization" (default) or "legacy"
        self.search_mode = search_mode or os.getenv("SEARCH_MODE", "integrated_vectorization")

        # FoundryChatClient Agent (populated by initialize())
        self._agent: Any = None
        self._initialized = False

        # Ensure the module-level search service matches the requested mode
        global _search_service
        if _search_service is None:
            if self.search_mode == "integrated_vectorization":
                _search_service = IntegratedVectorizationSearchService()
            else:
                _search_service = HRPolicySearchService()

    @property
    def search_service(self) -> Any:
        return _get_search_service()

    async def initialize(self) -> None:
        """Create the FoundryChatClient Agent. Call at application startup."""
        if self._initialized:
            return
        if not self.use_agent or not self.project_endpoint:
            logger.info("Agent mode disabled or no project endpoint; skipping agent creation")
            return
        if not AGENT_FRAMEWORK_AVAILABLE or FoundryChatClient is None:
            logger.warning("Agent framework not available; skipping agent creation")
            return

        try:
            credential = DefaultAzureCredential()  # type: ignore[misc]
            chat_client = FoundryChatClient(
                project_endpoint=self.project_endpoint,
                model=self.model_deployment_name,
                credential=credential,
            )

            self._agent = chat_client.as_agent(
                name="HRPolicyAgent",
                instructions=AGENT_INSTRUCTIONS,
                tools=[search_hr_policies],
            )

            self._initialized = True
            logger.info("HRPolicyAgent created via FoundryChatClient")

            # Optionally register in Foundry portal for visibility
            self._register_in_portal(credential)

        except Exception as e:
            logger.error("Failed to create FoundryChatClient Agent: %s", e)
            self._agent = None
            self._initialized = False

    def _register_in_portal(self, credential: Any) -> None:
        """Register the agent in Azure AI Foundry portal for monitoring."""
        try:
            from azure.ai.projects import AIProjectClient
            from azure.ai.projects.models import PromptAgentDefinition

            pc = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=credential,
            )
            try:
                existing = pc.agents.get(agent_name="HRPolicyAgent")
                logger.info("HRPolicyAgent already in Foundry portal")
            except Exception:
                pc.agents.create_version(
                    agent_name="HRPolicyAgent",
                    definition=PromptAgentDefinition(
                        model=self.model_deployment_name,
                        instructions=AGENT_INSTRUCTIONS,
                        temperature=0.0,
                    ),
                )
                logger.info("HRPolicyAgent registered in Foundry portal")
        except Exception as e:
            logger.debug("Portal registration skipped: %s", e)

    async def close(self) -> None:
        """Release local resources. The Foundry agent remains in the portal."""
        self._agent = None
        self._initialized = False

    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Answer an HR policy question using RAG.

        Returns:
            dict with answer, citations, confidence, and policy_references
        """
        if self.use_agent and self.project_endpoint:
            return await self._agent_answer(question, conversation_history)
        return await self._local_answer(question)

    async def _agent_answer(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Answer using the FoundryChatClient Agent with search_hr_policies tool."""
        if not self._initialized:
            await self.initialize()

        if not self._agent:
            logger.warning("Agent not available, falling back to local search")
            return await self._local_answer(question)

        try:
            prompt = self._build_prompt(question, conversation_history)
            result = await self._agent.run(prompt)
            response_text = str(result)
            return self._parse_agent_response(response_text, question)

        except Exception as e:
            logger.error("Agent answer failed: %s", e)
            return await self._local_answer(question)

    async def _local_answer(self, question: str) -> dict[str, Any]:
        """Answer using local search (no LLM, search results only)."""
        results = self.search_service.search(question, top=3)

        if not results:
            return {
                "answer": "I could not find relevant HR policy information for your question. "
                         "Please contact your HR representative for assistance.",
                "citations": [],
                "confidence": 0.0,
                "policy_references": [],
            }

        answer_parts = ["Based on the HR policy documents, here is what I found:\n"]
        citations = []
        policy_refs = []

        for i, result in enumerate(results, 1):
            title = result.get("title", result.get("parent_title", "Unknown Policy"))
            policy_num = result.get("policy_number", "")
            content = result.get("content", "")[:500]

            answer_parts.append(f"**{i}. {title}** (Policy {policy_num})")
            answer_parts.append(f"{content}\n")

            citations.append({
                "title": title,
                "policy_number": policy_num,
                "excerpt": content[:200],
            })
            if policy_num:
                policy_refs.append(f"Policy {policy_num} - {title}")

        answer_parts.append("\n*Note: This response is based on search results without AI summarization. "
                          "Enable Azure AI Foundry for enhanced responses.*")

        return {
            "answer": "\n".join(answer_parts),
            "citations": citations,
            "confidence": min(results[0].get("score", 0) / 10.0, 1.0) if results else 0.0,
            "policy_references": policy_refs,
        }

    def _build_prompt(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Build prompt with conversation context."""
        parts = []

        if conversation_history:
            parts.append("Previous conversation context:")
            for msg in conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role}: {content}")
            parts.append("")

        expanded_question = expand_query_with_glossary(question)
        parts.append(f"Employee Question: {expanded_question}")

        return "\n".join(parts)

    def _parse_agent_response(self, response_text: str, original_question: str) -> dict[str, Any]:
        """Parse agent response and extract citations."""
        citations = []
        policy_refs = []

        policy_pattern = r'\[?Policy\s+(\d+)\s*[-–]\s*([^\]]+)\]?'
        matches = re.findall(policy_pattern, response_text, re.IGNORECASE)
        for num, title in matches:
            citations.append({
                "policy_number": num,
                "title": title.strip(),
            })
            policy_refs.append(f"Policy {num} - {title.strip()}")

        return {
            "answer": response_text,
            "citations": citations,
            "confidence": 0.85 if citations else 0.6,
            "policy_references": list(set(policy_refs)),
        }

    def answer_question(self, question: str, conversation_history: Optional[list[dict[str, str]]] = None) -> dict[str, Any]:
        """Synchronous wrapper for answer_question_async."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_question_async(question, conversation_history))
        else:
            future = asyncio.ensure_future(
                self.answer_question_async(question, conversation_history),
                loop=loop,
            )
            return loop.run_until_complete(future)
