"""Foundry Hosted Agent — HR Policy

Exposes the ``HRPolicyAgent`` via the Foundry Responses protocol so it appears
in the Foundry portal and can be invoked through the standard Foundry endpoint
(``{project_endpoint}/agents/HRPolicyAgent/endpoint/protocols/openai/responses``).

This is an ALTERNATIVE hosting option to the in-process FastAPI host in
``src/backend/``. Both share the same agent logic and Azure AI Search index;
the hosted agent is the recommended deployment surface for production use with
Copilot Studio and other OpenAI-compatible clients.

References:
    Foundry Hosted Agents (Agent Framework):
        https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent?pivots=programming-language-python
    Hosted agents in Foundry Agent Service (preview):
        https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (injected by the Foundry platform at runtime)
# ---------------------------------------------------------------------------
PROJECT_ENDPOINT = os.environ.get(
    "FOUNDRY_PROJECT_ENDPOINT",
    os.environ.get("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT", ""),
)
MODEL = os.environ.get(
    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    os.environ.get("FOUNDRY_MODEL", os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")),
)
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_INDEX = os.environ.get(
    "AZURE_SEARCH_INDEX_NAME",
    os.environ.get("AZURE_SEARCH_INDEX", "hr-policy-index"),
)
AZURE_SEARCH_API_KEY = os.environ.get("AZURE_SEARCH_API_KEY")
AI_SEARCH_QUERY_TYPE = os.environ.get("AI_SEARCH_QUERY_TYPE", "semantic")
AI_SEARCH_SEMANTIC_CONFIG = os.environ.get(
    "AI_SEARCH_SEMANTIC_CONFIG", "hr-semantic-config"
)
AI_SEARCH_VECTOR_FIELD = os.environ.get("AI_SEARCH_VECTOR_FIELD", "policy_vector")
AI_SEARCH_CONTENT_FIELD = os.environ.get("AI_SEARCH_CONTENT_FIELD", "policy")
AI_SEARCH_TITLE_FIELD = os.environ.get("AI_SEARCH_TITLE_FIELD", "parent_title")
AI_SEARCH_POLICY_NUMBER_FIELD = os.environ.get(
    "AI_SEARCH_POLICY_NUMBER_FIELD", "policy_number"
)
AI_SEARCH_BLOB_URL_FIELD = os.environ.get("AI_SEARCH_BLOB_URL_FIELD", "blob_url")
AI_SEARCH_TOP_K = int(os.environ.get("AI_SEARCH_TOP_K", "5"))


# ---------------------------------------------------------------------------
# HR Glossary — vernacular -> formal policy terms
# Kept inline so the container image is self-contained.
# ---------------------------------------------------------------------------
HR_GLOSSARY: dict[str, str] = {
    "pto": "Paid Time Off",
    "paid time off": "Paid Time Off",
    "vacation": "Paid Time Off",
    "vacation time": "Paid Time Off",
    "sick leave": "Short-Term Disability",
    "sick time": "Short-Term Disability",
    "std": "Short-Term Disability",
    "short term disability": "Short-Term Disability",
    "ltd": "Long-Term Disability",
    "long term disability": "Long-Term Disability",
    "fmla": "Family and Medical Leave Act",
    "leave": "Types of Leave",
    "holiday": "Holiday Pay",
    "holiday pay": "Holiday Pay",
    "dress code": "Uniform Dress Code",
    "uniform": "Uniform Dress Code",
    "code of ethics": "Code of Ethics and Related Matters",
    "ethics": "Code of Ethics and Related Matters",
    "probation": "Probationary Period",
    "probationary": "Probationary Period",
    "rehire": "Rehiring of Retirees",
    "blood borne": "Blood Borne Pathogens",
    "bloodborne": "Blood Borne Pathogens",
    "hr generalist": "HR Generalist",
    "data management": "Data Management",
    "pre-employment": "Pre-employment Medical Examinations",
    "pre employment": "Pre-employment Medical Examinations",
    "medical exam": "Pre-employment Medical Examinations",
    "background check": "Pre-employment Medical Examinations",
    "career path": "Career Path",
}


def expand_query_with_glossary(query: str) -> str:
    """Append formal policy terms for any vernacular found in the query."""
    expansions: list[str] = []
    lowered = query.lower()
    seen: set[str] = set()
    for vernacular, formal in HR_GLOSSARY.items():
        if vernacular in lowered and formal.lower() not in lowered and formal not in seen:
            expansions.append(formal)
            seen.add(formal)
    if not expansions:
        return query
    return f"{query} {' '.join(expansions)}"


# ---------------------------------------------------------------------------
# Tool — Azure AI Search for HR policy documents
# ---------------------------------------------------------------------------
@tool(
    name="search_hr_policies",
    description=(
        "Search the HR policy knowledge base for relevant policies, "
        "procedures, and guidelines. Returns excerpts with policy numbers, "
        "titles, and source documents. Uses hybrid retrieval (text + vector "
        "+ semantic ranker) and expands HR vernacular (e.g. PTO, STD, dress "
        "code) via the HR glossary."
    ),
)
def search_hr_policies(
    query: Annotated[
        str,
        "The HR question or topic to search for "
        "(policy number, vernacular like 'PTO' or 'dress code', etc.)",
    ],
) -> str:
    """Search the HR policy index using Azure AI Search."""
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import DefaultAzureCredential as SyncCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizableTextQuery

    if not AZURE_SEARCH_ENDPOINT:
        return "Error: Azure AI Search endpoint not configured. Set AZURE_SEARCH_ENDPOINT."

    credential: Any = (
        AzureKeyCredential(AZURE_SEARCH_API_KEY)
        if AZURE_SEARCH_API_KEY
        else SyncCredential()
    )
    client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=credential,
    )

    expanded_query = expand_query_with_glossary(query)
    logger.info("Search query: %r -> expanded: %r", query, expanded_query)

    search_kwargs: dict[str, Any] = {
        "search_text": expanded_query,
        "query_type": AI_SEARCH_QUERY_TYPE,
        "top": AI_SEARCH_TOP_K,
    }
    if AI_SEARCH_QUERY_TYPE == "semantic":
        search_kwargs["semantic_configuration_name"] = AI_SEARCH_SEMANTIC_CONFIG

    # Hybrid leg: let Azure AI Search vectorize the query at query time using
    # the index's AzureOpenAIVectorizer.
    try:
        search_kwargs["vector_queries"] = [
            VectorizableTextQuery(
                text=expanded_query,
                k_nearest_neighbors=AI_SEARCH_TOP_K,
                fields=AI_SEARCH_VECTOR_FIELD,
            )
        ]
    except Exception as exc:
        logger.debug("VectorizableTextQuery unavailable, text-only search: %s", exc)

    try:
        results = client.search(**search_kwargs)
    except Exception as exc:
        logger.error("Azure AI Search query failed: %s", exc)
        return f"Error querying Azure AI Search: {exc}"

    parts: list[str] = []
    for i, result in enumerate(results, 1):
        title = result.get(AI_SEARCH_TITLE_FIELD, "Unknown Policy")
        policy_num = result.get(AI_SEARCH_POLICY_NUMBER_FIELD, "")
        content = result.get(AI_SEARCH_CONTENT_FIELD, "")[:1500]
        blob_url = result.get(AI_SEARCH_BLOB_URL_FIELD, "")
        score = result.get("@search.score", 0)
        reranker = result.get("@search.reranker_score")

        score_info = f"score: {score:.2f}"
        if reranker:
            score_info += f", reranker: {reranker:.2f}"

        policy_line = f"Policy {policy_num} - {title}" if policy_num else title
        parts.append(
            f"[Result {i}] ({score_info})\n"
            f"{policy_line}\n"
            + (f"Source: {blob_url}\n" if blob_url else "")
            + f"{content}\n"
        )

    return "\n---\n".join(parts) if parts else f"No results found for query: {query}"


# ---------------------------------------------------------------------------
# Agent Instructions
# ---------------------------------------------------------------------------
HR_POLICY_INSTRUCTIONS = """\
You are an HR Policy Assistant for the "Ask HR" system.
Your role is to answer employee questions based ONLY on the internal HR policy
documents retrieved from the knowledge base.

You have access to a `search_hr_policies` tool that searches the HR policy
knowledge base using hybrid retrieval (text + vector + semantic ranker).
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


# ---------------------------------------------------------------------------
# Create Agent + Server
# ---------------------------------------------------------------------------
# GenAI tracing (best-effort; captures agent/model/tool calls as spans).
if os.environ.get("ENABLE_TRACING", "true").lower() == "true":
    try:
        from src.observability import enable_tracing

        enable_tracing()
    except Exception as _trace_exc:  # pragma: no cover - never block hosting
        logger.warning("GenAI tracing not enabled: %s", _trace_exc)

credential = DefaultAzureCredential()

# Retrieval mode: "tool" (default classic @tool search), "context-semantic"
# (classic search via the out-of-the-box context provider), or "context-agentic"
# (agentic retrieval over the Foundry IQ knowledge base). The context-provider
# modes run retrieval automatically before each turn.
RETRIEVAL_MODE = os.environ.get("RETRIEVAL_MODE", "tool").lower()

_tools: list[Any] = [search_hr_policies]
_context_providers: list[Any] | None = None
_instructions = HR_POLICY_INSTRUCTIONS

if RETRIEVAL_MODE in ("context-semantic", "context-agentic", "semantic", "agentic"):
    try:
        from src.search.agentic_context_provider import build_search_context_provider

        _context_providers = [
            build_search_context_provider(
                RETRIEVAL_MODE,
                endpoint=AZURE_SEARCH_ENDPOINT,
                index_name=AZURE_SEARCH_INDEX,
                api_key=AZURE_SEARCH_API_KEY,
                top_k=AI_SEARCH_TOP_K,
            )
        ]
        _tools = []
        logger.info("Hosted agent RAG mode: %s (context provider)", RETRIEVAL_MODE)
    except Exception as _rag_exc:  # pragma: no cover - never block hosting
        logger.warning(
            "Context provider unavailable (%s); using classic search tool.", _rag_exc
        )

agent = Agent(
    client=FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL,
        credential=credential,
    ),
    name="HRPolicyAgent",
    instructions=_instructions,
    tools=_tools,
    context_providers=_context_providers,
    # The hosting infrastructure manages conversation history, so don't
    # have the agent persist messages itself.
    default_options={"store": False},
)

server = ResponsesHostServer(agent)


if __name__ == "__main__":
    server.run()
