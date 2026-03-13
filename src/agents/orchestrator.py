"""
HR Policy Knowledge Workflow Orchestrator

Uses Agent Framework's Sequential Workflow pattern to coordinate:
1. Document Ingestion (Custom Executor - no LLM)
2. Query Understanding with Glossary (Custom Executor - no LLM)
3. Policy Retrieval via AI Search (Agent + Custom Executor)
4. Answer Generation (AI Agent)

Reference: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/sequential
"""

import logging
import os
import time
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Agent Framework imports
try:
    from agent_framework import (
        Executor,
        WorkflowBuilder,
        WorkflowContext,
        WorkflowOutputEvent,
        WorkflowStatusEvent,
        ExecutorFailedEvent,
        WorkflowFailedEvent,
        WorkflowRunState,
        handler,
    )
    from typing_extensions import Never
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    logger.warning("agent-framework not installed, sequential workflows unavailable")
    # Provide stub classes so the module can still be imported
    class Executor:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs): pass
    def handler(f): return f  # type: ignore[no-redef]

from src.search.search_service import HRPolicySearchService, expand_query_with_glossary, HR_GLOSSARY


# =============================================================================
# DATA STRUCTURES
# =============================================================================

WorkflowState = Dict[str, Any]


# =============================================================================
# STEP 1: Query Understanding Executor (no LLM)
# =============================================================================

class QueryUnderstandingExecutor(Executor):
    """
    Step 1: Understand the user's query by expanding vernacular terms.

    This addresses the "difficulty understanding technician vernacular" challenge.
    Maps shorthand, coded identifiers, and informal terms to formal HR policy names.
    """

    def __init__(self):
        super().__init__(id="query_understanding")

    @handler
    async def process(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        logger.info("Step 1: Query Understanding")

        original_query = state.get("query", "")
        expanded_query = expand_query_with_glossary(original_query)

        # Detect matched glossary terms
        matched_terms = []
        query_lower = original_query.lower()
        for vernacular, formal in HR_GLOSSARY.items():
            if vernacular in query_lower:
                matched_terms.append({"vernacular": vernacular, "formal": formal})

        state["original_query"] = original_query
        state["expanded_query"] = expanded_query
        state["matched_glossary_terms"] = matched_terms
        state["query_understanding_complete"] = True

        logger.info(f"Query expanded: '{original_query}' -> '{expanded_query}'")
        if matched_terms:
            logger.info(f"Glossary matches: {matched_terms}")

        await ctx.send_message(state)


# =============================================================================
# STEP 2: Policy Retrieval Executor (Azure AI Search)
# =============================================================================

class PolicyRetrievalExecutor(Executor):
    """
    Step 2: Retrieve relevant HR policies from Azure AI Search.

    Uses the expanded query from Step 1 for better search results.
    """

    def __init__(self):
        self._search_service: Optional[HRPolicySearchService] = None
        super().__init__(id="policy_retrieval")

    @property
    def search_service(self) -> HRPolicySearchService:
        if self._search_service is None:
            self._search_service = HRPolicySearchService()
        return self._search_service

    @handler
    async def process(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        logger.info("Step 2: Policy Retrieval")

        query = state.get("expanded_query", state.get("query", ""))
        results = self.search_service.search(query, top=5)

        state["search_results"] = results
        state["search_results_count"] = len(results)
        state["policy_retrieval_complete"] = True

        logger.info(f"Retrieved {len(results)} policy documents")
        await ctx.send_message(state)


# =============================================================================
# STEP 3: Answer Generation Executor (AI Agent)
# =============================================================================

class AnswerGenerationExecutor(Executor):
    """
    Step 3: Generate a grounded answer using the retrieved policy documents.

    Uses the HR Policy Agent with Azure AI Search for RAG-based generation.
    Falls back to search-result-only responses if agent not available.
    """

    def __init__(self, project_endpoint: str = ""):
        self.project_endpoint = project_endpoint
        self._agent = None
        super().__init__(id="answer_generation", is_terminal=True)

    @property
    def agent(self):
        if self._agent is None:
            from src.agents.hr_policy_agent import HRPolicyAgent
            self._agent = HRPolicyAgent(
                use_agent=bool(self.project_endpoint),
                project_endpoint=self.project_endpoint,
            )
        return self._agent

    @handler
    async def process(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        logger.info("Step 3: Answer Generation")

        question = state.get("original_query", state.get("query", ""))
        conversation_history = state.get("conversation_history", [])
        search_results = state.get("search_results", [])

        # If we have search results but no agent, build answer from results
        if not self.project_endpoint and search_results:
            answer_parts = ["Based on the HR policy documents:\n"]
            citations = []
            policy_refs = []

            for i, result in enumerate(search_results[:3], 1):
                title = result.get("title", "Unknown")
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

            state["answer"] = "\n".join(answer_parts)
            state["citations"] = citations
            state["policy_references"] = policy_refs
            state["confidence"] = 0.7
        else:
            # Use AI agent for answer generation
            result = await self.agent.answer_question_async(question, conversation_history)
            state["answer"] = result.get("answer", "")
            state["citations"] = result.get("citations", [])
            state["policy_references"] = result.get("policy_references", [])
            state["confidence"] = result.get("confidence", 0.0)

        state["answer_generation_complete"] = True
        logger.info("Answer generation complete")
        await ctx.send_message(state)


# =============================================================================
# WORKFLOW ORCHESTRATOR
# =============================================================================

class HRPolicyWorkflowOrchestrator:
    """
    Sequential Workflow Orchestrator for HR Policy Knowledge Agent.

    Uses Agent Framework's WorkflowBuilder pattern:

    ┌─────────────────────────┐
    │  QueryUnderstanding     │  ← Custom Executor (NO LLM)
    │  Executor               │    Glossary expansion, term mapping
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  PolicyRetrieval        │  ← Custom Executor (NO LLM)
    │  Executor               │    Azure AI Search query
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  AnswerGeneration       │  ← AI Agent (Terminal)
    │  Executor               │    RAG-based answer with citations
    └─────────────────────────┘
    """

    def __init__(self, use_azure: bool = True):
        self.use_azure = use_azure
        self.project_endpoint = os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")

    def _build_workflow(self) -> Any:
        """Build the sequential workflow with all executors."""
        if not WORKFLOW_AVAILABLE:
            raise RuntimeError("agent-framework package not installed. Cannot build workflow.")

        query_executor = QueryUnderstandingExecutor()
        retrieval_executor = PolicyRetrievalExecutor()
        answer_executor = AnswerGenerationExecutor(
            project_endpoint=self.project_endpoint if self.use_azure else "",
        )

        workflow = (
            WorkflowBuilder()
            .set_start_executor(query_executor)
            .add_edge(query_executor, retrieval_executor)
            .add_edge(retrieval_executor, answer_executor)
            .build()
        )
        return workflow

    async def answer_question_async(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Process an HR question through the sequential workflow.

        Args:
            question: The employee's HR question
            conversation_history: Optional previous messages

        Returns:
            Complete workflow results with answer, citations, etc.
        """
        start_time = time.time()

        if not WORKFLOW_AVAILABLE:
            # Fallback: run steps manually without workflow framework
            return await self._fallback_answer(question, conversation_history)

        initial_state: WorkflowState = {
            "query": question,
            "conversation_history": conversation_history or [],
        }

        try:
            workflow = self._build_workflow()
            output_event = None

            async for event in workflow.run_stream(question):
                if isinstance(event, WorkflowStatusEvent):
                    if event.state == WorkflowRunState.IN_PROGRESS:
                        logger.debug("Workflow in progress...")
                elif isinstance(event, WorkflowOutputEvent):
                    output_event = event
                elif isinstance(event, (ExecutorFailedEvent, WorkflowFailedEvent)):
                    logger.error(f"Workflow failed: {event}")
                    break

            if output_event and output_event.data:
                result = output_event.data
            else:
                result = await self._fallback_answer(question, conversation_history)

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            result = await self._fallback_answer(question, conversation_history)

        elapsed_ms = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = elapsed_ms
        return result

    async def _fallback_answer(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Fallback: run steps manually without workflow framework."""
        from src.agents.hr_policy_agent import HRPolicyAgent

        agent = HRPolicyAgent(
            use_agent=bool(self.project_endpoint) and self.use_azure,
            project_endpoint=self.project_endpoint,
        )
        return await agent.answer_question_async(question, conversation_history)

    def answer_question(
        self,
        question: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Synchronous wrapper."""
        import asyncio
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.answer_question_async(question, conversation_history))
        else:
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.answer_question_async(question, conversation_history))
