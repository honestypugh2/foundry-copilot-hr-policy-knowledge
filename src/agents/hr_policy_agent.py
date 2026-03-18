"""
HR Policy Agent

RAG-based agent that answers employee questions using Azure AI Search
to retrieve relevant HR policy documents and Azure OpenAI for generation.

Uses Azure AI Foundry Agent Framework (agent_framework) with
AzureAIClient for grounded, citation-backed responses.

The agent is created once at startup via initialize() and persists
in the Azure AI Foundry portal for visibility and management.
"""

import asyncio
import logging
import os
import re
from typing import Annotated, Any, Optional

logger = logging.getLogger(__name__)

# Agent Framework imports
try:
    from agent_framework.azure import AzureAIClient
    from azure.identity.aio import DefaultAzureCredential
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    AzureAIClient = None
    DefaultAzureCredential = None
    logger.warning("agent-framework not installed, agent mode unavailable")

from src.search.search_service import HRPolicySearchService, expand_query_with_glossary


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


class HRPolicyAgent:
    """
    HR Policy Agent that uses RAG to answer employee HR questions.

    The agent is created once via initialize() and persists in the
    Azure AI Foundry portal for visibility and management.

    Modes:
    1. Azure AI Agent (with AzureAIClient + AI Search tool) — persistent
    2. Local search fallback (no LLM)
    """

    def __init__(
        self,
        use_agent: bool = True,
        project_endpoint: Optional[str] = None,
        model_deployment_name: Optional[str] = None,
        search_index_name: Optional[str] = None,
        search_connection_id: Optional[str] = None,
    ):
        self.use_agent = use_agent and AGENT_FRAMEWORK_AVAILABLE
        # Prefer AZURE_AI_PROJECT_ENDPOINT (Foundry project format: services.ai.azure.com)
        # over AZURE_AI_FOUNDRY_PROJECT_ENDPOINT which may be an OpenAI endpoint
        self.project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT", "")
        self.model_deployment_name = model_deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.search_index_name = search_index_name or os.getenv("AZURE_SEARCH_INDEX_NAME", "hr-policy-index")
        self.search_connection_id = search_connection_id or os.getenv("AI_SEARCH_PROJECT_CONNECTION_ID", "")

        # Foundry agent state (populated by initialize())
        self._credential: Any = None
        self._agent: Any = None
        self._agent_cm: Any = None
        self._initialized = False

        # Local search service for fallback
        self.search_service = HRPolicySearchService()

    async def initialize(self) -> None:
        """
        Create the Foundry agent once. Call at application startup.

        The agent persists in the Azure AI Foundry portal and is reused
        across all subsequent requests.
        """
        if self._initialized:
            return
        if not self.use_agent or not self.project_endpoint:
            logger.info("Agent mode disabled or no project endpoint; skipping Foundry agent creation")
            return
        if not AGENT_FRAMEWORK_AVAILABLE or AzureAIClient is None or DefaultAzureCredential is None:
            logger.warning("Agent framework not available; skipping Foundry agent creation")
            return

        try:
            self._credential = DefaultAzureCredential()

            tools: list[Any] = [self.format_hr_query_context]
            if self.search_connection_id:
                tools.append(self._build_azure_ai_search_tool())

            self._agent_cm = AzureAIClient(
                project_endpoint=self.project_endpoint,
                model_deployment_name=self.model_deployment_name,
                credential=self._credential,
            ).as_agent(
                name="HRPolicyAgent",
                instructions=AGENT_INSTRUCTIONS,
                description="HR Policy Assistant - answers employee questions from internal HR documents",
                tools=tools,
            )
            self._agent = await self._agent_cm.__aenter__()
            self._initialized = True
            logger.info("HRPolicyAgent created and persisted in Foundry portal")
        except Exception as e:
            logger.error(f"Failed to create Foundry agent: {e}")
            self._agent = None
            self._initialized = False

    async def close(self) -> None:
        """Release local resources on shutdown. The agent remains in the Foundry portal.

        NOTE: We intentionally do NOT call __aexit__ on the agent context
        manager — that would delete the agent from Foundry. We only close
        the credential and underlying HTTP sessions to avoid resource leaks.
        """
        # Close the agent's internal HTTP client if accessible
        if self._agent:
            for attr in ("_client", "client"):
                client = getattr(self._agent, attr, None)
                if client and hasattr(client, "close"):
                    try:
                        await client.close()
                    except Exception:
                        pass
                    break
        if self._credential:
            try:
                await self._credential.close()
            except Exception:
                pass
            self._credential = None
        self._agent = None
        self._agent_cm = None
        self._initialized = False

    def _build_azure_ai_search_tool(self) -> dict:
        """Build the Azure AI Search tool configuration for the agent."""
        return {
            "type": "azure_ai_search",
            "azure_ai_search": {
                "indexes": [{
                    "project_connection_id": self.search_connection_id,
                    "index_name": self.search_index_name,
                    "query_type": "semantic",
                }]
            },
        }

    @staticmethod
    def format_hr_query_context(
        query: Annotated[str, "The employee's HR question to search for"],
    ) -> str:
        """Format and expand the employee's HR query with glossary terms for better search."""
        expanded = expand_query_with_glossary(query)
        return f"Search for HR policy information about: {expanded}"

    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Answer an HR policy question using RAG.

        Args:
            question: The employee's question
            conversation_history: Optional previous messages for context

        Returns:
            dict with answer, citations, confidence, and policy_references
        """
        if self.use_agent and self.project_endpoint:
            return await self._agent_answer(question, conversation_history)
        else:
            return await self._local_answer(question)

    async def _agent_answer(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Answer using the persisted Foundry agent with AI Search RAG."""
        # Lazy-initialize if not done at startup
        if not self._initialized:
            await self.initialize()

        if not self._agent:
            logger.warning("Foundry agent not available, falling back to local")
            return await self._local_answer(question)

        response_text = ""
        try:
            prompt = self._build_prompt(question, conversation_history)

            stream = self._agent.run(prompt, stream=True)
            async for chunk in stream:
                if chunk.text:
                    response_text += str(chunk.text)
            await stream.get_final_response()

            return self._parse_agent_response(response_text, question)

        except Exception as e:
            logger.error(f"Agent answer failed: {e}")
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

        # Build answer from search results
        answer_parts = ["Based on the HR policy documents, here is what I found:\n"]
        citations = []
        policy_refs = []

        for i, result in enumerate(results, 1):
            title = result.get("title", "Unknown Policy")
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
            for msg in conversation_history[-5:]:  # Last 5 messages
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

        # Extract policy references from response (e.g., [Policy 50410 - ...])
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
