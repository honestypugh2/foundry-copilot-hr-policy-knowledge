#!/usr/bin/env python3
"""
Pattern 2: Foundry Agent Action — Agentic Retrieval via Foundry IQ

Creates a Foundry Agent with an MCP tool connected to an Azure AI Search
Knowledge Base. Copilot Studio invokes this agent as an Action rather than
querying Azure AI Search directly as a Knowledge Source.

Workflow:
    1. Ensure Azure AI Search index exists (populated by Pattern 1 Option 1 or 2)
    2. Create a Knowledge Source pointing to the search index
    3. Create a Knowledge Base that wraps the Knowledge Source(s)
    4. Create an MCP connection in the Foundry project
    5. Create a Foundry Agent with the knowledge_base_retrieve MCP tool
    6. Copilot Studio calls the agent via Foundry Agent Action

Advantages over Pattern 1 (direct Knowledge Source):
    - Agentic retrieval: AI plans and routes queries across sources
    - Multi-source aggregation for complex queries
    - Custom retrieval + answer instructions
    - Source attribution in responses
    - Can combine multiple search indexes into one knowledge base

Prerequisites:
    - Azure AI Search index populated (run Pattern 1 Option 1 or 2 first)
    - Azure AI Foundry project with managed identity
    - RBAC: Search Index Data Reader on project managed identity
    - RBAC: Search Service Contributor on your user identity

Shared configuration: src/config/search_config.json
    - Same index, synonym map, semantic config as Pattern 1

Usage:
    python scripts/create_foundry_agent.py
    python scripts/create_foundry_agent.py --verify-only
    python scripts/create_foundry_agent.py --cleanup

References:
    - Foundry IQ: https://github.com/Azure/Copilot-Studio-and-Azure/blob/main/labs/2.4-microsoft-foundry-agentic-retrieval/notebooks/foundry-IQ-agents.ipynb
    - Knowledge Base API: https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.search_config import search_cfg

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential, get_bearer_token_provider
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndexKnowledgeSource,
        SearchIndexKnowledgeSourceParameters,
        SearchIndexFieldReference,
        KnowledgeBase,
        KnowledgeRetrievalMinimalReasoningEffort,
        KnowledgeRetrievalMediumReasoningEffort,
        KnowledgeRetrievalOutputMode,
        KnowledgeSourceReference,
    )
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import PromptAgentDefinition, MCPTool
    FOUNDRY_SDK_AVAILABLE = True
except ImportError as e:
    FOUNDRY_SDK_AVAILABLE = False
    logger.warning("Required SDK packages not installed: %s", e)
    logger.info("Install: pip install azure-search-documents>=11.7.0b2 azure-ai-projects>=2.0.0b1 azure-identity")


# ---------------------------------------------------------------------------
# Configuration from search_config.json
# ---------------------------------------------------------------------------
INDEX_NAME = search_cfg.index_name
AGENTIC_CFG = search_cfg.agentic_retrieval
FOUNDRY_CFG = search_cfg.foundry_agent

KNOWLEDGE_SOURCE_NAME = search_cfg.knowledge_source_name
KNOWLEDGE_BASE_NAME = search_cfg.knowledge_base_name
MCP_CONNECTION_NAME = search_cfg.mcp_connection_name

# Agent config
AGENT_NAME = "HRPolicyAgent"
AGENT_MODEL = FOUNDRY_CFG.get("model", "gpt-4o")


def _get_credential():
    try:
        return AzureCliCredential(process_timeout=30)
    except Exception:
        return DefaultAzureCredential()


# ---------------------------------------------------------------------------
# Step 1: Create Knowledge Source
# ---------------------------------------------------------------------------
def create_knowledge_source() -> None:
    """Create a Knowledge Source pointing to the HR policy search index."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    credential = _get_credential()
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)

    # Build source data fields from config
    source_fields = [
        SearchIndexFieldReference(name=f)
        for f in AGENTIC_CFG.get("source_data_fields", ["id", "policy", "parent_title", "policy_number"])
    ]

    ks = SearchIndexKnowledgeSource(
        name=KNOWLEDGE_SOURCE_NAME,
        description=AGENTIC_CFG.get("knowledge_source_description",
                                    f"Knowledge source for HR policy documents indexed in {INDEX_NAME}"),
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=INDEX_NAME,
            source_data_fields=source_fields,
        ),
    )

    index_client.create_or_update_knowledge_source(ks)
    logger.info("Knowledge Source '%s' created → index '%s'", KNOWLEDGE_SOURCE_NAME, INDEX_NAME)


# ---------------------------------------------------------------------------
# Step 2: Create Knowledge Base
# ---------------------------------------------------------------------------
def create_knowledge_base() -> None:
    """Create a Knowledge Base wrapping the Knowledge Source(s)."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    credential = _get_credential()
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)

    # Determine reasoning effort
    effort_str = AGENTIC_CFG.get("retrieval_reasoning_effort", "medium")
    if effort_str == "minimal":
        reasoning_effort = KnowledgeRetrievalMinimalReasoningEffort()
    else:
        reasoning_effort = KnowledgeRetrievalMediumReasoningEffort()

    # Determine output mode
    output_mode_str = AGENTIC_CFG.get("output_mode", "EXTRACTIVE")
    if output_mode_str.upper() == "EXTRACTIVE":
        output_mode = KnowledgeRetrievalOutputMode.EXTRACTIVE_DATA
    else:
        output_mode = KnowledgeRetrievalOutputMode.EXTRACTIVE_DATA

    kb = KnowledgeBase(
        name=KNOWLEDGE_BASE_NAME,
        description=f"HR policy knowledge base with agentic retrieval over {INDEX_NAME}",
        knowledge_sources=[KnowledgeSourceReference(name=KNOWLEDGE_SOURCE_NAME)],
        output_mode=output_mode,
        retrieval_reasoning_effort=reasoning_effort,
    )

    index_client.create_or_update_knowledge_base(knowledge_base=kb)
    logger.info("Knowledge Base '%s' created with source '%s'", KNOWLEDGE_BASE_NAME, KNOWLEDGE_SOURCE_NAME)


# ---------------------------------------------------------------------------
# Step 3: Create MCP Connection
# ---------------------------------------------------------------------------
def create_mcp_connection() -> str:
    """Create a project connection for the MCP tool to access the knowledge base."""
    import requests

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    project_resource_id = os.getenv("PROJECT_RESOURCE_ID", "")
    mcp_api_version = AGENTIC_CFG.get("mcp", {}).get("api_version", "2025-11-01-Preview")

    if not project_resource_id:
        logger.error("PROJECT_RESOURCE_ID not set. Set it to your Foundry project ARM resource ID.")
        return ""

    mcp_endpoint = f"{search_endpoint}/knowledgebases/{KNOWLEDGE_BASE_NAME}/mcp?api-version={mcp_api_version}"

    credential = _get_credential()
    token_provider = get_bearer_token_provider(credential, "https://management.azure.com/.default")

    headers = {
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json",
    }

    response = requests.put(
        f"https://management.azure.com{project_resource_id}/connections/{MCP_CONNECTION_NAME}?api-version=2025-10-01-preview",
        headers=headers,
        json={
            "name": MCP_CONNECTION_NAME,
            "type": "Microsoft.MachineLearningServices/workspaces/connections",
            "properties": {
                "authType": "ProjectManagedIdentity",
                "category": "RemoteTool",
                "target": mcp_endpoint,
                "isSharedToAll": True,
                "audience": "https://search.azure.com/",
                "metadata": {"ApiType": "Azure"},
            },
        },
    )

    if response.status_code in (200, 201):
        logger.info("MCP Connection '%s' created → %s", MCP_CONNECTION_NAME, mcp_endpoint)
        return mcp_endpoint
    else:
        logger.error("MCP Connection creation failed (%d): %s", response.status_code, response.text)
        return ""


# ---------------------------------------------------------------------------
# Step 4: Create Foundry Agent
# ---------------------------------------------------------------------------
def create_foundry_agent(mcp_endpoint: str) -> None:
    """Create a Foundry Agent with MCP tool access to the knowledge base."""
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT", "")
    if not project_endpoint:
        logger.error("AZURE_AI_PROJECT_ENDPOINT not set")
        return

    credential = _get_credential()
    project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)

    # Agent instructions
    retrieval_instructions = FOUNDRY_CFG.get("retrieval_instructions", "")
    answer_instructions = FOUNDRY_CFG.get("answer_instructions", "")

    instructions = f"""You are an HR Policy Assistant with access to the company's HR policy knowledge base via Foundry IQ.

## YOUR KNOWLEDGE SOURCE:
HR Policy Knowledge Base ({KNOWLEDGE_BASE_NAME})
- All company HR policies indexed from the ASK HR Knowledge library
- Includes: hiring, leave, dress code, career paths, IT policies, operational matters
- Synonym map for HR vernacular (PTO, dress code, hiring, etc.)

## HOW TO RESPOND:

**Step 1: ALWAYS call the knowledge_base_retrieve tool first**
- Search for relevant information before answering
- Use descriptive search queries related to the user's question

**Step 2: Read and understand the retrieved content**
- The tool returns relevant passages from HR policy documents
- Each result includes the source document and content

**Step 3: Provide a comprehensive answer WITH CITATIONS**
- Use the retrieved information to answer the question
- Always cite the policy number and title
- Format: "According to Policy [number] - [title], ..."

## RETRIEVAL GUIDELINES:
{retrieval_instructions}

## ANSWER GUIDELINES:
{answer_instructions}

## IMPORTANT:
- ALWAYS search the knowledge base first — do not answer from general knowledge
- ALWAYS include policy number citations
- If the policy is not found, say so clearly
- Never provide legal advice
- Be helpful and provide actionable guidance"""

    # Create MCP tool
    mcp_tool = MCPTool(
        server_label="hr-knowledge",
        server_url=mcp_endpoint,
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=MCP_CONNECTION_NAME,
    )

    # Create the agent
    agent = project_client.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=AGENT_MODEL,
            instructions=instructions,
            tools=[mcp_tool],
        ),
    )

    logger.info("Foundry Agent '%s' created (version %s, model %s)",
                agent.name, agent.version, AGENT_MODEL)
    logger.info("  Agent ID: %s", agent.id)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. In Copilot Studio, add a Foundry Agent Action")
    logger.info("  2. Connect to agent '%s' version %s", agent.name, agent.version)
    logger.info("  3. Create a topic that invokes this agent action")
    logger.info("  4. Publish to Teams / Web Chat")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def verify() -> None:
    """Verify all resources exist."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    credential = _get_credential()
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)

    # Check index
    try:
        index = index_client.get_index(INDEX_NAME)
        logger.info("  Index '%s': %d fields", INDEX_NAME, len(index.fields))
    except Exception as e:
        logger.error("  Index '%s': NOT FOUND — %s", INDEX_NAME, e)

    # Check knowledge source
    try:
        ks = index_client.get_knowledge_source(KNOWLEDGE_SOURCE_NAME)
        logger.info("  Knowledge Source '%s': OK", KNOWLEDGE_SOURCE_NAME)
    except Exception as e:
        logger.error("  Knowledge Source '%s': NOT FOUND — %s", KNOWLEDGE_SOURCE_NAME, e)

    # Check knowledge base
    try:
        kb = index_client.get_knowledge_base(KNOWLEDGE_BASE_NAME)
        logger.info("  Knowledge Base '%s': %d sources", KNOWLEDGE_BASE_NAME, len(kb.knowledge_sources or []))
    except Exception as e:
        logger.error("  Knowledge Base '%s': NOT FOUND — %s", KNOWLEDGE_BASE_NAME, e)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
def cleanup() -> None:
    """Delete all Foundry IQ resources (Knowledge Base → Knowledge Source)."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    credential = _get_credential()
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)

    # Delete KB first (references KS)
    try:
        index_client.delete_knowledge_base(KNOWLEDGE_BASE_NAME)
        logger.info("Deleted Knowledge Base '%s'", KNOWLEDGE_BASE_NAME)
        time.sleep(2)
    except Exception:
        logger.info("Knowledge Base '%s' not found (OK)", KNOWLEDGE_BASE_NAME)

    # Delete KS
    try:
        index_client.delete_knowledge_source(KNOWLEDGE_SOURCE_NAME)
        logger.info("Deleted Knowledge Source '%s'", KNOWLEDGE_SOURCE_NAME)
    except Exception:
        logger.info("Knowledge Source '%s' not found (OK)", KNOWLEDGE_SOURCE_NAME)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(verify_only: bool = False, do_cleanup: bool = False) -> None:
    if not FOUNDRY_SDK_AVAILABLE:
        logger.error("Required SDK packages not installed")
        return

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if not search_endpoint:
        logger.error("AZURE_SEARCH_ENDPOINT not set")
        return

    if do_cleanup:
        cleanup()
        return

    if verify_only:
        logger.info("=== Verifying resources ===")
        verify()
        return

    logger.info("=== Pattern 2: Foundry Agent Action Setup ===")
    logger.info("")

    logger.info("Step 1: Create Knowledge Source")
    create_knowledge_source()

    logger.info("")
    logger.info("Step 2: Create Knowledge Base")
    create_knowledge_base()

    logger.info("")
    logger.info("Step 3: Create MCP Connection")
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    mcp_api_version = AGENTIC_CFG.get("mcp", {}).get("api_version", "2025-11-01-Preview")
    mcp_endpoint = f"{search_endpoint}/knowledgebases/{KNOWLEDGE_BASE_NAME}/mcp?api-version={mcp_api_version}"
    result = create_mcp_connection()
    if not result:
        logger.warning("MCP connection creation failed — agent will use direct endpoint")

    logger.info("")
    logger.info("Step 4: Create Foundry Agent")
    create_foundry_agent(mcp_endpoint)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pattern 2: Foundry Agent Action — Agentic Retrieval via Foundry IQ"
    )
    parser.add_argument("--verify-only", action="store_true", help="Verify resources exist")
    parser.add_argument("--cleanup", action="store_true", help="Delete KB + KS resources")
    args = parser.parse_args()
    run(verify_only=args.verify_only, do_cleanup=args.cleanup)
