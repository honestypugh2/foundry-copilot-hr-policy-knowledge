"""HR Policy Agent — Agent Framework with FoundryChatClient

Uses Agent Framework's ``Agent`` class with ``FoundryChatClient`` and
``@tool``-decorated methods for Azure AI Search retrieval + RAG-based answer
generation, mirroring the pattern used in:

- https://github.com/honestypugh2/foundry-dealer-portal-chat/blob/main/src/api/app/agents/dealer_agent.py
- https://github.com/honestypugh2/foundry-grant-eo-validation-demo/blob/main/src/agents/compliance_agent.py

The agent autonomously searches Azure AI Search via its ``@tool`` method
(hybrid: text + vector + semantic ranker) and returns grounded, citation-backed
answers using the HR policy index defined in ``src/config/search_config.json``.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Annotated, Any, Dict, List, Optional

from src.config.model_policy import get_chat_model
from src.config.search_config import search_cfg
from src.search.search_service import expand_query_with_glossary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent Framework imports
# ---------------------------------------------------------------------------
try:
    from agent_framework import Agent, tool
    from agent_framework.foundry import FoundryChatClient
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    logger.warning("agent-framework not installed")

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizableTextQuery
    SEARCH_SDK_AVAILABLE = True
except ImportError:
    SEARCH_SDK_AVAILABLE = False
    logger.warning("azure-search-documents not installed")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
HR_POLICY_SYSTEM_PROMPT = """You are an HR Policy Assistant for the "Ask HR" system.
Your role is to answer employee questions based ONLY on the internal HR policy
documents retrieved from the knowledge base.

You have access to a `search_hr_policies` tool that searches the HR policy
knowledge base using hybrid retrieval (full-text + vector + semantic ranker).
You MUST use this tool to find relevant policies before answering. Never answer
from general knowledge.

CRITICAL RULES:
1. Always call `search_hr_policies` first with a focused query.
2. Only answer based on the retrieved policy documents.
3. If the information is not found, respond:
   "I could not find this information in the HR policy documents. Please contact
   your HR representative for assistance."
4. Always cite the specific policy number and title when referencing information.
5. Be precise — do not paraphrase in ways that change meaning.
6. If a question is ambiguous, ask for clarification.
7. Handle vernacular terms (e.g., "PTO" -> "Paid Time Off", "dress code" ->
   "Uniform Dress Code") — the search tool already expands these via a glossary.

OUTPUT FORMAT:
- Start with a direct answer to the question.
- Include specific policy citations: [Policy XXXXX - Title].
- Quote relevant sections when precision matters.
- End with "Source: [Policy Number - Policy Title]" for each referenced policy.
"""


# System prompt for the context-provider modes (RETRIEVAL_MODE=context-*), where
# relevant HR policy excerpts are retrieved and injected automatically before
# each turn instead of via an explicit search tool.
HR_POLICY_CONTEXT_SYSTEM_PROMPT = """You are an HR Policy Assistant for the "Ask HR" system.
Relevant HR policy excerpts are automatically retrieved and provided to you as
context before each question. Answer employee questions using ONLY that provided
context.

CRITICAL RULES:
1. Only answer based on the retrieved HR policy context provided to you.
2. If the information is not present in the context, respond:
   "I could not find this information in the HR policy documents. Please contact
   your HR representative for assistance."
3. Always cite the specific policy number and title when referencing information.
4. Be precise — do not paraphrase in ways that change meaning.
5. Handle vernacular terms (e.g., "PTO" -> "Paid Time Off").

OUTPUT FORMAT:
- Start with a direct answer to the question.
- Include specific policy citations: [Policy XXXXX - Title].
- Quote relevant sections when precision matters.
- End with "Source: [Policy Number - Policy Title]" for each referenced policy.
"""


class HRPolicyAgent:
    """HR Policy Agent using Agent Framework + FoundryChatClient.

    The agent autonomously calls ``search_hr_policies`` via the Agent Framework
    tool-calling loop. Configuration falls back to environment variables and
    the shared ``search_cfg`` so this matches the rest of the repo.
    """

    def __init__(
        self,
        project_endpoint: str = "",
        model_deployment_name: str = "",
        search_index_name: str = "",
        search_endpoint: Optional[str] = None,
        search_api_key: Optional[str] = None,
        search_query_type: str = "semantic",
        retrieval_mode: Optional[str] = None,
    ) -> None:
        # Retrieval mode selects how the Agent Framework path does RAG:
        #   "tool"             -> custom @tool classic search (default)
        #   "context-semantic" -> AzureAISearchContextProvider, classic search
        #   "context-agentic"  -> AzureAISearchContextProvider, agentic retrieval
        #                         over the Foundry IQ knowledge base
        self.retrieval_mode = (
            retrieval_mode or os.getenv("RETRIEVAL_MODE", "tool")
        ).lower()
        self.project_endpoint = project_endpoint or os.getenv(
            "AZURE_AI_PROJECT_ENDPOINT",
            os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT", ""),
        )
        self.model_deployment_name = get_chat_model(model_deployment_name)
        self.search_index_name = (
            search_index_name
            or os.getenv("AZURE_SEARCH_INDEX_NAME")
            or search_cfg.index_name
        )
        self.search_endpoint = search_endpoint or os.getenv("AZURE_SEARCH_ENDPOINT", "")
        self.search_api_key = search_api_key or os.getenv("AZURE_SEARCH_API_KEY")
        self.search_query_type = search_query_type
        self.semantic_configuration_name = os.getenv(
            "AI_SEARCH_SEMANTIC_CONFIG", search_cfg.semantic_configuration
        )

        # Field names — pulled from the shared config so they stay in sync
        # with the index schema created by the indexing scripts.
        self._content_field = search_cfg.content_field
        self._source_field = search_cfg.source_field
        self._vector_field = search_cfg.vector_field
        self._parent_title_field = search_cfg.parent_title_field
        self._policy_number_field = search_cfg.policy_number_field
        self._blob_url_field = search_cfg.blob_url_field
        self._top_k = search_cfg.top_k

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the agent (idempotent).

        Pure Microsoft Agent Framework path — no portal registration.
        The Foundry portal version is provisioned separately by
        ``src.agents.create_foundry_agent`` (Pattern B), and the optional
        Hosted Agent variant is described by ``src/hosted_agent/agent.yaml``.
        """
        if self._initialized:
            return
        self._initialized = True

    async def close(self) -> None:
        """Release resources."""
        self._initialized = False

    # ------------------------------------------------------------------
    # Tool: Azure AI Search for HR policy documents
    # ------------------------------------------------------------------
    @tool(
        name="search_hr_policies",
        description=(
            "Search the HR policy knowledge base for relevant policies, "
            "procedures, and guidelines. Returns excerpts with policy numbers, "
            "titles, and source documents. Uses hybrid retrieval (full-text + "
            "vector + semantic ranker) and expands HR vernacular (e.g. PTO, "
            "STD, dress code) via the HR glossary."
        ),
    )
    def search_hr_policies(
        self,
        query: Annotated[
            str,
            "The HR question or topic to search for "
            "(policy number, vernacular terms like 'PTO' or 'dress code', etc.)",
        ],
    ) -> str:
        """Search the HR policy index using Azure AI Search."""
        if not self.search_endpoint:
            return "Error: Azure AI Search endpoint not configured. Set AZURE_SEARCH_ENDPOINT."

        if not SEARCH_SDK_AVAILABLE:
            return "Error: azure-search-documents SDK not installed."

        if self.search_api_key and not self.search_api_key.startswith("your_"):
            credential: Any = AzureKeyCredential(self.search_api_key)
        else:
            try:
                credential = AzureCliCredential()
            except Exception:
                credential = DefaultAzureCredential()

        # Expand vernacular HR terms before searching (e.g. PTO -> Paid Time Off)
        expanded_query = expand_query_with_glossary(query)

        client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index_name,
            credential=credential,
        )

        search_kwargs: Dict[str, Any] = {
            "search_text": expanded_query,
            "query_type": self.search_query_type,
            "top": self._top_k,
        }
        if self.search_query_type == "semantic":
            search_kwargs["semantic_configuration_name"] = self.semantic_configuration_name

        # Hybrid leg: let Azure AI Search vectorize the query at query time
        # using the index's AzureOpenAIVectorizer.
        try:
            search_kwargs["vector_queries"] = [
                VectorizableTextQuery(
                    text=expanded_query,
                    k_nearest_neighbors=self._top_k,
                    fields=self._vector_field,
                )
            ]
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("VectorizableTextQuery unavailable, text-only search: %s", e)

        try:
            results = client.search(**search_kwargs)
        except Exception as e:
            logger.error("Azure AI Search query failed: %s", e)
            return f"Error querying Azure AI Search: {e}"

        output_parts: List[str] = []
        for i, result in enumerate(results, 1):
            title = result.get(self._parent_title_field, "Unknown Policy")
            policy_num = result.get(self._policy_number_field, "")
            content = result.get(self._content_field, "")[:1500]
            blob_url = result.get(self._blob_url_field, "")
            score = result.get("@search.score", 0)
            reranker = result.get("@search.reranker_score")

            score_info = f"score: {score:.2f}"
            if reranker:
                score_info += f", reranker: {reranker:.2f}"

            header = f"[Result {i}] ({score_info})"
            policy_line = f"Policy {policy_num} - {title}" if policy_num else title
            output_parts.append(
                f"{header}\n"
                f"{policy_line}\n"
                + (f"Source: {blob_url}\n" if blob_url else "")
                + f"{content}\n"
            )

        if not output_parts:
            return f"No relevant HR policies found for query: {query}"

        return "\n---\n".join(output_parts)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate a grounded answer using Agent Framework + FoundryChatClient.

        Args:
            question: The employee's HR question.
            conversation_history: Previous conversation turns (role/content dicts).

        Returns:
            Dict with ``answer``, ``citations``, ``policy_references``, ``confidence``.
        """
        if not AGENT_FRAMEWORK_AVAILABLE or not self.project_endpoint:
            logger.warning(
                "Agent Framework or project endpoint unavailable; returning empty answer"
            )
            return self._empty_response()

        try:
            return await self._generate_with_agent_framework(question, conversation_history)
        except Exception as e:
            logger.error("Agent Framework failed: %s", e)
            return {
                "answer": (
                    "I encountered an error while searching the HR policy "
                    "knowledge base. Please try again or contact your HR representative."
                ),
                "citations": [],
                "policy_references": [],
                "confidence": 0.0,
            }

    async def _generate_with_agent_framework(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate the answer using ``Agent`` + ``FoundryChatClient``."""
        try:
            credential = AzureCliCredential()
        except Exception:
            credential = DefaultAzureCredential()

        client = FoundryChatClient(
            project_endpoint=self.project_endpoint,
            model=self.model_deployment_name,
            credential=credential,
        )

        # Select the RAG strategy based on retrieval_mode:
        #   context-semantic / context-agentic -> out-of-the-box context provider
        #   tool (default)                      -> custom @tool classic search
        from src.search.agentic_context_provider import is_context_mode

        tools: list[Any] = []
        context_providers: list[Any] = []
        instructions = HR_POLICY_SYSTEM_PROMPT
        use_tool_steps = True

        if is_context_mode(self.retrieval_mode):
            try:
                from src.search.agentic_context_provider import (
                    build_search_context_provider,
                )

                context_providers = [
                    build_search_context_provider(
                        self.retrieval_mode,
                        endpoint=self.search_endpoint,
                        index_name=self.search_index_name,
                        api_key=self.search_api_key,
                        top_k=self._top_k,
                    )
                ]
                instructions = HR_POLICY_CONTEXT_SYSTEM_PROMPT
                use_tool_steps = False
            except Exception as e:
                logger.warning(
                    "Search context provider unavailable (%s); "
                    "falling back to the classic search tool.",
                    e,
                )
                tools = [self.search_hr_policies]
        else:
            tools = [self.search_hr_policies]

        agent = Agent(
            client=client,
            name="HRPolicyAgent",
            instructions=instructions,
            tools=tools,
            context_providers=context_providers or None,
        )

        prompt = self._build_prompt(
            question, conversation_history, use_tool_steps=use_tool_steps
        )

        # Stream the agent response
        response_text = ""
        async for chunk in agent.run(prompt, stream=True):
            if getattr(chunk, "text", None):
                response_text += chunk.text

        citations, policy_refs = self._extract_citations_from_text(response_text)

        return {
            "answer": response_text,
            "citations": citations,
            "policy_references": policy_refs,
            "confidence": 0.85 if citations else (0.6 if response_text else 0.0),
        }

    # ------------------------------------------------------------------
    # Prompt + citation helpers
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_tool_steps: bool = True,
    ) -> str:
        """Build the prompt for the agent including conversation context.

        When ``use_tool_steps`` is ``False`` (context-provider modes), the prompt
        omits the explicit "call the search tool" step because retrieval runs
        automatically before each turn.
        """
        prompt = f"Answer the following HR policy question:\n\n{question}"

        if conversation_history:
            history_text = "\n".join(
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conversation_history[-6:]
            )
            prompt += f"\n\nPREVIOUS CONVERSATION:\n{history_text}"

        if use_tool_steps:
            prompt += (
                "\n\nPlease perform the following steps:\n"
                "1. Use the search_hr_policies tool to find relevant HR policies.\n"
                "2. Analyze the retrieved excerpts for the specific information requested.\n"
                "3. Provide a clear, grounded answer with policy number citations "
                "in the format [Policy XXXXX - Title].\n"
                "4. End with 'Source: [Policy Number - Policy Title]' for each "
                "referenced policy."
            )
        else:
            prompt += (
                "\n\nUse the retrieved HR policy context provided to you to answer. "
                "Provide a clear, grounded answer with policy number citations in "
                "the format [Policy XXXXX - Title], and end with "
                "'Source: [Policy Number - Policy Title]' for each referenced policy."
            )

        return prompt

    def _extract_citations_from_text(
        self, text: str
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Extract policy citations of the form ``Policy 12345 - Title`` from text."""
        citations: List[Dict[str, Any]] = []
        policy_refs: List[str] = []
        seen: set[str] = set()

        # [Policy 12345 - Title] or "Policy 12345 - Title"
        pattern = r"\[?Policy\s+(\d{3,6})\s*[-–—:]\s*([^\]\n]+?)\]?(?=[\.,;\n]|$)"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            num = match.group(1).strip()
            title = match.group(2).strip().rstrip(".]")
            key = f"{num}|{title.lower()}"
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                {
                    "policy_number": num,
                    "title": title,
                }
            )
            policy_refs.append(f"Policy {num} - {title}")

        return citations, policy_refs

    def _empty_response(self) -> Dict[str, Any]:
        return {
            "answer": (
                "Agent Framework is not configured. Please set "
                "AZURE_AI_PROJECT_ENDPOINT and install agent-framework."
            ),
            "citations": [],
            "policy_references": [],
            "confidence": 0.0,
        }

    # ------------------------------------------------------------------
    # Sync wrapper
    # ------------------------------------------------------------------
    def answer_question(
        self,
        question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for ``answer_question_async``."""
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_question_async(question, conversation_history))
        else:
            import nest_asyncio  # type: ignore[import-not-found]

            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.answer_question_async(question, conversation_history)
            )


async def main() -> None:
    """Example usage of the HR Policy Agent."""
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    agent = HRPolicyAgent(
        project_endpoint=(
            os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            or os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
            or ""
        ),
        model_deployment_name=get_chat_model(),
        search_index_name=(
            os.getenv("AZURE_SEARCH_INDEX_NAME") or search_cfg.index_name
        ),
        search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        search_api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        search_query_type=os.getenv("AI_SEARCH_QUERY_TYPE", "semantic"),
    )

    await agent.initialize()

    sample_question = "How much PTO do part-time employees accrue?"
    print("Answering question using Agent Framework + FoundryChatClient...\n")
    result = await agent.answer_question_async(sample_question)
    print(f"Answer:\n{result['answer'][:1500]}")
    print(f"\nCitations: {len(result['citations'])}")
    print(f"Policy references: {result['policy_references']}")
    print(f"Confidence: {result['confidence']}")

    await agent.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
