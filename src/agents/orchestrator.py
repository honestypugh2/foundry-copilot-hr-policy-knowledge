"""
HR Policy Knowledge Workflow Orchestrator

Uses Agent Framework's SequentialBuilder to coordinate:
1. QueryUnderstandingExecutor  (custom Executor — no LLM, glossary expansion)
2. PolicyRetrievalExecutor     (custom Executor — Azure AI Search)
3. FoundryChatClient Agent     (answer synthesis with search context)
4. FinalAnswerExecutor         (custom Executor — extracts structured result)

References:
    Agent Framework + FoundryChatClient:
        https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry
    Sequential Workflow + Custom Executors:
        https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent Framework imports
# ---------------------------------------------------------------------------
WORKFLOW_AVAILABLE = False
try:
    from agent_framework import (
        Agent,
        AgentExecutorResponse,
        AgentResponse,
        Executor,
        Message,
        WorkflowContext,
        handler,
    )
    from agent_framework.foundry import FoundryChatClient
    from agent_framework.orchestrations import SequentialBuilder
    from azure.identity import DefaultAzureCredential
    WORKFLOW_AVAILABLE = True
except ImportError:
    logger.warning("agent-framework not installed, sequential workflows unavailable")

from src.search.search_service import HRPolicySearchService, expand_query_with_glossary, HR_GLOSSARY
from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService

# Reuse the canonical agent instructions from hr_policy_agent
from src.agents.hr_policy_agent import AGENT_INSTRUCTIONS


# =============================================================================
# STEP 1: Query Understanding Executor (no LLM)
# =============================================================================

if WORKFLOW_AVAILABLE:

    class QueryUnderstandingExecutor(Executor):
        """
        Step 1: Expand vernacular terms using the HR glossary.

        Receives the user query as a Message, performs glossary expansion,
        and forwards the enriched state as JSON to the next executor.
        """

        def __init__(self):
            super().__init__(id="query_understanding")

        @handler
        async def process(
            self,
            messages: List[Message],
            ctx: WorkflowContext[List[Message]],
        ) -> None:
            original_query = messages[-1].text.strip()
            logger.info("Step 1: Query Understanding")

            expanded_query = expand_query_with_glossary(original_query)

            matched_terms = []
            query_lower = original_query.lower()
            for vernacular, formal in HR_GLOSSARY.items():
                if vernacular in query_lower:
                    matched_terms.append({"vernacular": vernacular, "formal": formal})

            state = {
                "user_query": original_query,
                "expanded_query": expanded_query,
                "matched_glossary_terms": matched_terms,
            }

            logger.info("Query expanded: '%s' -> '%s'", original_query, expanded_query)
            if matched_terms:
                logger.info("Glossary matches: %s", matched_terms)

            state_json = json.dumps(state, default=str)
            await ctx.send_message(
                messages + [Message("assistant", [state_json], author_name="query_understanding")]
            )

    # =============================================================================
    # STEP 2: Policy Retrieval Executor (Azure AI Search — no LLM)
    # =============================================================================

    class PolicyRetrievalExecutor(Executor):
        """
        Step 2: Retrieve relevant HR policies from Azure AI Search.

        Uses the expanded query from Step 1.
        """

        def __init__(self, search_mode: str = "integrated_vectorization"):
            self._search_service: Any = None
            self._search_mode = search_mode
            super().__init__(id="policy_retrieval")

        @property
        def search_service(self) -> Any:
            if self._search_service is None:
                if self._search_mode == "integrated_vectorization":
                    self._search_service = IntegratedVectorizationSearchService()
                else:
                    self._search_service = HRPolicySearchService()
            return self._search_service

        @handler
        async def process(
            self,
            messages: List[Message],
            ctx: WorkflowContext[List[Message]],
        ) -> None:
            state = json.loads(messages[-1].text)
            logger.info("Step 2: Policy Retrieval")

            query = state.get("expanded_query", state.get("user_query", ""))
            results = self.search_service.search(query, top=5)

            # Serialise search results (drop non-serialisable fields)
            serialisable_results = []
            for r in results:
                serialisable_results.append({
                    "title": r.get("title", r.get("parent_title", "Unknown")),
                    "policy_number": r.get("policy_number", ""),
                    "content": r.get("content", "")[:800],
                    "score": r.get("score", 0),
                    "source": r.get("source", ""),
                })

            state["search_results"] = serialisable_results
            state["search_results_count"] = len(serialisable_results)

            logger.info("Retrieved %d policy documents", len(serialisable_results))

            state_json = json.dumps(state, default=str)
            await ctx.send_message(
                messages + [Message("assistant", [state_json], author_name="policy_retrieval")]
            )

    # =============================================================================
    # STEP 4: Final Answer Executor (terminal — captures Agent response)
    # =============================================================================

    class FinalAnswerExecutor(Executor):
        """
        Terminal executor that captures the FoundryChatClient Agent's response
        and yields a structured result dict as the workflow output.
        """

        def __init__(self):
            super().__init__(id="final_answer")

        @handler
        async def process(
            self,
            agent_response: AgentExecutorResponse,
            ctx: WorkflowContext[List[Message], Dict[str, Any]],
        ) -> None:
            conversation = agent_response.full_conversation
            if not conversation:
                await ctx.yield_output(
                    {"answer": "No conversation to process.", "citations": [], "confidence": 0.0, "policy_references": []}
                )
                return

            # Extract the last state JSON and the agent's answer
            state: Optional[dict] = None
            agent_answer: Optional[str] = None

            for msg in reversed(list(conversation)):
                if msg.role == "assistant" and msg.text:
                    try:
                        parsed = json.loads(msg.text)
                        if isinstance(parsed, dict) and "user_query" in parsed:
                            if state is None or len(parsed) > len(state):
                                state = parsed
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    if agent_answer is None:
                        agent_answer = msg.text

            if state is None:
                state = {}
            if agent_answer is None:
                agent_answer = "The agent did not produce a response."

            import re
            citations = []
            policy_refs = []
            policy_pattern = r'\[?Policy\s+(\d+)\s*[-–]\s*([^\]]+)\]?'
            for num, title in re.findall(policy_pattern, agent_answer, re.IGNORECASE):
                citations.append({"policy_number": num, "title": title.strip()})
                policy_refs.append(f"Policy {num} - {title.strip()}")

            result = {
                "answer": agent_answer,
                "citations": citations,
                "confidence": 0.85 if citations else 0.6,
                "policy_references": list(set(policy_refs)),
                "search_results_count": state.get("search_results_count", 0),
                "matched_glossary_terms": state.get("matched_glossary_terms", []),
            }

            result_json = json.dumps(result, default=str)
            await ctx.send_message(
                list(conversation)
                + [Message("assistant", [result_json], author_name="final_answer")]
            )
            await ctx.yield_output(result)


# =============================================================================
# WORKFLOW ORCHESTRATOR
# =============================================================================

class HRPolicyWorkflowOrchestrator:
    """
    Sequential Workflow Orchestrator using Agent Framework + FoundryChatClient.

    Pipeline:
        QueryUnderstandingExecutor (custom)
        → PolicyRetrievalExecutor (custom)
        → FoundryChatClient Agent (answer synthesis)
        → FinalAnswerExecutor (custom — terminal)

    ┌─────────────────────────┐
    │  QueryUnderstanding     │  ← Custom Executor (NO LLM)
    │  Executor               │    Glossary expansion, term mapping
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  PolicyRetrieval        │  ← Custom Executor (NO LLM)
    │  Executor               │    Azure AI Search hybrid query
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  FoundryChatClient      │  ← FoundryChatClient Agent (LLM)
    │  Agent                  │    Synthesise answer from search results
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  FinalAnswerExecutor    │  ← Custom Executor (Terminal)
    │                         │    Extract structured result
    └─────────────────────────┘
    """

    def __init__(self, use_azure: bool = True, search_mode: str = "integrated_vectorization"):
        self.use_azure = use_azure
        self.search_mode = search_mode
        self.project_endpoint = (
            os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
            or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            or os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
        )
        self.model = (
            os.getenv("FOUNDRY_MODEL")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        )
        self._hr_agent = None  # cached HRPolicyAgent for fallback path

    async def initialize(self) -> None:
        """Pre-create the HRPolicyAgent so it is ready for the fallback path."""
        from src.agents.hr_policy_agent import HRPolicyAgent
        self._hr_agent = HRPolicyAgent(
            use_agent=bool(self.project_endpoint) and self.use_azure,
            project_endpoint=self.project_endpoint,
            model_deployment_name=self.model,
            search_mode=self.search_mode,
        )
        await self._hr_agent.initialize()

    async def close(self) -> None:
        """Release local resources; the Foundry agent remains in the portal."""
        if self._hr_agent:
            await self._hr_agent.close()
            self._hr_agent = None

    # ------------------------------------------------------------------
    # FoundryChatClient Agent (Step 3)
    # ------------------------------------------------------------------

    def _create_foundry_agent(self) -> Agent:
        """Create a FoundryChatClient-backed Agent for answer synthesis."""
        credential = DefaultAzureCredential()
        chat_client = FoundryChatClient(
            project_endpoint=self.project_endpoint,
            model=self.model,
            credential=credential,
        )
        return chat_client.as_agent(
            name="HRPolicyAnswerSynthesis",
            instructions=AGENT_INSTRUCTIONS,
        )

    # ------------------------------------------------------------------
    # Workflow builder
    # ------------------------------------------------------------------

    def _build_workflow(self) -> Any:
        """
        Build the sequential workflow mixing custom Executors with
        a FoundryChatClient Agent.

        Pipeline:
            QueryUnderstandingExecutor → PolicyRetrievalExecutor
            → FoundryChatClient Agent → FinalAnswerExecutor
        """
        query_executor = QueryUnderstandingExecutor()
        retrieval_executor = PolicyRetrievalExecutor(search_mode=self.search_mode)
        foundry_agent = self._create_foundry_agent()
        final_executor = FinalAnswerExecutor()

        workflow = SequentialBuilder(
            participants=[
                query_executor,
                retrieval_executor,
                foundry_agent,
                final_executor,
            ]
        ).build()

        return workflow

    # ------------------------------------------------------------------
    # Async entry-point
    # ------------------------------------------------------------------

    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Process an HR question through the sequential workflow.

        Returns:
            Complete workflow results with answer, citations, etc.
        """
        start_time = time.time()

        if not WORKFLOW_AVAILABLE or not self.project_endpoint or not self.use_azure:
            result = await self._fallback_answer(question, conversation_history)
            elapsed_ms = int((time.time() - start_time) * 1000)
            result["processing_time_ms"] = elapsed_ms
            return result

        try:
            workflow = self._build_workflow()

            output_data = None
            async for event in workflow.run(question, stream=True):
                if event.type == "status":
                    logger.debug("Workflow state: %s", event.data)
                elif event.type == "output":
                    output_data = event.data
                    logger.info("Workflow output received")
                elif event.type == "executor_failed":
                    details = event.data
                    logger.error(
                        "Executor failed: %s: %s",
                        getattr(details, "executor_id", "unknown"),
                        getattr(details, "message", str(details)),
                    )
                elif event.type == "failed":
                    details = event.data
                    logger.error(
                        "Workflow failed: %s",
                        getattr(details, "message", str(details)),
                    )

            # Extract result from workflow output
            if output_data is not None:
                if isinstance(output_data, AgentResponse):
                    for msg in reversed(output_data.messages):
                        if msg.text:
                            try:
                                result = json.loads(msg.text)
                                elapsed_ms = int((time.time() - start_time) * 1000)
                                result["processing_time_ms"] = elapsed_ms
                                return result
                            except (json.JSONDecodeError, TypeError):
                                continue
                elif isinstance(output_data, dict):
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    output_data["processing_time_ms"] = elapsed_ms
                    return output_data

            logger.warning("No structured output from workflow, falling back")

        except Exception as e:
            logger.error("Workflow execution failed: %s", e)

        result = await self._fallback_answer(question, conversation_history)
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = elapsed_ms
        return result

    async def _fallback_answer(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Fallback: use HRPolicyAgent directly without the workflow."""
        if not self._hr_agent:
            from src.agents.hr_policy_agent import HRPolicyAgent
            self._hr_agent = HRPolicyAgent(
                use_agent=bool(self.project_endpoint) and self.use_azure,
                project_endpoint=self.project_endpoint,
                model_deployment_name=self.model,
                search_mode=self.search_mode,
            )
            await self._hr_agent.initialize()
        return await self._hr_agent.answer_question_async(question, conversation_history)

    def answer_question(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Synchronous wrapper."""
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
