"""
HR Policy Agent

RAG-based agent that answers employee questions using Azure AI Search
to retrieve relevant HR policy documents and Azure OpenAI for generation.

Uses Azure AI Foundry Agent Framework (agent_framework) with
AzureAIProjectAgentProvider for grounded, citation-backed responses.
"""

import asyncio
import json
import logging
import os
import re
from typing import Annotated, Any, Optional

logger = logging.getLogger(__name__)

# Agent Framework imports
try:
    from agent_framework.azure import AzureAIProjectAgentProvider
    from azure.identity.aio import AzureCliCredential
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    AzureAIProjectAgentProvider = None
    AzureCliCredential = None
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

    Modes:
    1. Azure AI Agent (with AzureAIProjectAgentProvider + AI Search tool)
    2. Local search + LLM fallback
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
        self.project_endpoint = project_endpoint or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
        self.model_deployment_name = model_deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.search_index_name = search_index_name or os.getenv("AZURE_SEARCH_INDEX_NAME", "hr-policy-index")
        self.search_connection_id = search_connection_id or os.getenv("AI_SEARCH_PROJECT_CONNECTION_ID", "")

        # Local search service for fallback
        self.search_service = HRPolicySearchService()

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
        """Answer using Azure AI Agent Framework with AI Search RAG."""
        if not AGENT_FRAMEWORK_AVAILABLE or AzureAIProjectAgentProvider is None or AzureCliCredential is None:
            logger.warning("Agent framework not available, falling back to local")
            return await self._local_answer(question)

        response_text = ""
        try:
            # Create fresh credentials (avoid pickle issues in workflow framework)
            async with (
                AzureCliCredential() as credential,
                AzureAIProjectAgentProvider(credential=credential) as provider,
            ):
                # Build tools list
                tools = [self.format_hr_query_context]
                tool_resources = {}

                # Add Azure AI Search tool if connection is configured
                if self.search_connection_id:
                    tools.append(self._build_azure_ai_search_tool())

                agent = await provider.create_agent(
                    name="HRPolicyAgent",
                    instructions=AGENT_INSTRUCTIONS,
                    description="HR Policy Assistant - answers employee questions from internal HR documents",
                    model=self.model_deployment_name,
                    tools=tools,
                    tool_resources=tool_resources,
                )

                # Build prompt with conversation context
                prompt = self._build_prompt(question, conversation_history)

                # Stream agent response
                async for chunk in agent.run_stream(prompt):
                    if chunk.text:
                        response_text += str(chunk.text)

                # Clean up agent
                await provider.delete_agent(agent.id)

            return self._parse_agent_response(response_text, question)

        except Exception as e:
            logger.error(f"Agent answer failed: {e}")
            # Fall back to local search
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
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_question_async(question, conversation_history))
        else:
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.answer_question_async(question, conversation_history))
