"""
FastAPI Backend for HR Policy Knowledge Agent

Provides REST API endpoints for:
- Chat-based HR policy Q&A
- Knowledge base management
- Document upload and indexing
- Azure service health checks
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    KnowledgeBaseInfo,
)
from src.agents.orchestrator import HRPolicyWorkflowOrchestrator
from src.search.search_service import HRPolicySearchService, HR_GLOSSARY
from src.document_processing.document_ingestion import DocumentIngestionAgent
from src.copilot_studio.service import CopilotStudioService
from src.observability import enable_tracing

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------- global singletons ----------

orchestrator: Optional[HRPolicyWorkflowOrchestrator] = None
search_service: Optional[HRPolicySearchService] = None
ingestion_agent: Optional[DocumentIngestionAgent] = None
copilot_studio: Optional[CopilotStudioService] = None

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge_base" / "ASK HR Knowledge"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared services on startup."""
    global orchestrator, search_service, ingestion_agent, copilot_studio

    # Wire GenAI tracing first so agent/model/tool calls are captured as spans.
    if os.getenv("ENABLE_TRACING", "true").lower() == "true":
        try:
            enable_tracing()
        except Exception as e:  # best-effort; never block startup
            logger.warning(f"Tracing setup failed: {e}")

    use_azure = os.getenv("USE_AZURE_SERVICES", "true").lower() == "true"
    orchestrator = HRPolicyWorkflowOrchestrator(use_azure=use_azure)

    # Create and persist the Foundry agent at startup
    try:
        await orchestrator.initialize()
        logger.info("HR Policy Agent initialised and persisted in Foundry portal")
    except Exception as e:
        logger.warning(f"Foundry agent initialisation failed (will retry on first request): {e}")

    try:
        search_service = HRPolicySearchService()
        logger.info("Azure AI Search service initialised")
    except Exception as e:
        logger.warning(f"Azure AI Search unavailable: {e}")
        search_service = None

    try:
        ingestion_agent = DocumentIngestionAgent()
        logger.info("Document ingestion agent initialised")
    except Exception as e:
        logger.warning(f"Document ingestion agent unavailable: {e}")
        ingestion_agent = None

    try:
        copilot_studio = CopilotStudioService()
        logger.info("Copilot Studio service initialised")
    except Exception as e:
        logger.warning(f"Copilot Studio service unavailable: {e}")
        copilot_studio = None

    yield

    # cleanup — agent remains in Foundry portal
    if orchestrator:
        await orchestrator.close()
    orchestrator = None
    search_service = None
    ingestion_agent = None
    copilot_studio = None


app = FastAPI(
    title="HR Policy Knowledge Agent API",
    description="AI-powered HR policy Q&A backed by Azure AI Search and Agent Framework",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS – restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================================================== #
#  HEALTH / STATUS                                                           #
# ========================================================================== #


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check for all Azure services."""
    from src.models.schemas import ServiceStatus

    ai_search_ok = False
    try:
        if search_service:
            search_service.get_document_count()
            ai_search_ok = True
    except Exception:
        pass

    azure_openai_ok = bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
    di_ok = bool(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"))
    ai_foundry_ok = bool(
        os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
        or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    )

    services = {
        "ai_search": ServiceStatus(
            name="Azure AI Search",
            status="healthy" if ai_search_ok else "unavailable",
            details="Connected" if ai_search_ok else "Not connected",
        ),
        "azure_openai": ServiceStatus(
            name="Azure OpenAI",
            status="configured" if azure_openai_ok else "unavailable",
            details="Endpoint configured" if azure_openai_ok else "No endpoint set",
        ),
        "document_intelligence": ServiceStatus(
            name="Azure Document Intelligence",
            status="configured" if di_ok else "unavailable",
            details="Endpoint configured" if di_ok else "No endpoint set",
        ),
        "ai_foundry": ServiceStatus(
            name="Microsoft Foundry",
            status="available" if ai_foundry_ok else "unavailable",
            details="Project endpoint configured" if ai_foundry_ok else "No project endpoint",
        ),
    }

    all_ok = ai_search_ok and azure_openai_ok
    status = "healthy" if all_ok else "degraded"

    return HealthResponse(
        status=status,
        message="All services operational" if all_ok else "Some services unavailable",
        version=app.version,
        services=services,
    )


# ========================================================================== #
#  CHAT                                                                      #
# ========================================================================== #


def _pattern_a_answer(question: str) -> dict:
    """Pattern A — direct hybrid search, no LLM, no Foundry agent.

    Mirrors what Copilot Studio's native Knowledge Source connector does
    against ``hr-policy-index`` (full-text + vector + semantic ranker via
    integrated vectorization), but returns it as a backend response so
    the same routing decision can be tested from non-Copilot-Studio
    callers (frontend, Pattern C composite flows).

    No LLM call \u2014 the answer is a deterministic concatenation of the top
    hits with their policy numbers and titles. Use Pattern B
    (``ORCHESTRATOR_PATTERN=B``) when you want force-grounded synthesis.
    """
    from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService
    from src.search.search_service import expand_query_with_glossary

    iv_search = IntegratedVectorizationSearchService()
    expanded = expand_query_with_glossary(question or "")
    hits = iv_search.search(expanded, top=3)

    if not hits:
        return {
            "answer": "I could not find a relevant HR policy. Please contact your HR representative for assistance.",
            "citations": [],
            "policy_references": [],
            "confidence": 0.0,
            "matched_glossary_terms": [],
        }

    citations: list[dict] = []
    policy_refs: list[str] = []
    snippets: list[str] = []
    for hit in hits:
        policy_num = hit.get("policy_number", "")
        title = hit.get("title", "") or hit.get("parentTitle", "")
        content = hit.get("content", "")
        if policy_num and title:
            citations.append({"policy_number": policy_num, "title": title})
            policy_refs.append(f"Policy {policy_num} - {title}")
        if content:
            snippets.append(f"[Policy {policy_num} - {title}]\n{content[:400].strip()}")

    answer = "\n\n".join(snippets) if snippets else "Relevant HR policy documents were located but contain no extractable content."

    return {
        "answer": answer,
        "citations": citations,
        "policy_references": list(dict.fromkeys(policy_refs)),
        "confidence": 0.7 if citations else 0.4,
        "matched_glossary_terms": [],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer an HR policy question.

    Routing is controlled by ``ORCHESTRATOR_PATTERN`` (default ``A``):

    - **A** \u2014 Direct hybrid search via integrated vectorization, no LLM,
      no Foundry agent. ~1\u20132 s. Mirrors the Copilot Studio Knowledge
      Source connector behavior.
    - **B** \u2014 Foundry Agent Service prompt agent + MCPTool with
      ``tool_choice="required"`` for force-grounded synthesis. ~10\u201314 s.

    Pattern C (``/api/lookup``) is always available regardless of this
    setting. See [docs/RetrievalPatterns.md](../../docs/RetrievalPatterns.md).
    """
    pattern = os.getenv("ORCHESTRATOR_PATTERN", "A").strip().upper()
    start = time.time()

    if pattern == "A":
        try:
            result = _pattern_a_answer(request.message)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Search service unavailable: {e}")
    else:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialised")
        conversation = (
            [m.model_dump() for m in request.conversation_history]
            if request.conversation_history
            else []
        )
        result = await orchestrator.answer_question_async(
            question=request.message,
            conversation_history=conversation,
        )

    elapsed_ms = int((time.time() - start) * 1000)

    return ChatResponse(
        answer=result.get("answer", "I could not find a relevant HR policy."),
        citations=result.get("citations", []),
        policy_references=result.get("policy_references", []),
        confidence=result.get("confidence", 0.0),
        glossary_matches=result.get("matched_glossary_terms", []),
        processing_time_ms=elapsed_ms,
    )


# ========================================================================== #
#  LOOKUP — fast policy locator (no LLM, no MCP)                             #
# ========================================================================== #


@app.post("/api/lookup")
async def lookup(request: ChatRequest):
    """Look up the storage location of an HR policy document.

    Mirrors the canonical ``file_metadata_lookup`` tool from
    honestypugh2/foundry-copilot-search-validate
    (``src/agents/orchestrator_pattern_b.py``):
    a direct hybrid search over the index returning metadata fields only
    (``policy_number``, ``parent_title``, ``metadata_storage_name``,
    ``metadata_storage_path``, ``blob_url``, ``score``). No MCP call, no
    knowledge-base retrieval, no LLM synthesis. Typical latency ~1-2s vs
    ~10-14s for ``/api/chat``.

    Used by Copilot Studio Pattern C (Dual-Tool Routing) when the user
    asks WHERE a document is located, asks for a file path, URL, link,
    blob storage path, or document location. Do NOT use this endpoint
    for content/policy questions — route those to ``/api/chat`` or to
    the Copilot Studio knowledge source.
    """
    from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService
    from src.search.search_service import expand_query_with_glossary

    start = time.time()
    try:
        iv_search = IntegratedVectorizationSearchService()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Search service unavailable: {e}")

    query = expand_query_with_glossary(request.message or "")
    results = iv_search.search(query, top=3)

    documents = []
    for r in results:
        documents.append({
            "policy_number": r.get("policy_number", ""),
            "parent_title": r.get("parentTitle", r.get("title", "")),
            "metadata_storage_name": r.get("fileName", ""),
            "metadata_storage_path": r.get("filePath", ""),
            "blob_url": r.get("blob_url", ""),
            "score": r.get("score", 0.0),
        })

    elapsed_ms = int((time.time() - start) * 1000)
    return {
        "query": request.message,
        "expanded_query": query,
        "documents": documents,
        "total": len(documents),
        "processing_time_ms": elapsed_ms,
    }


# ========================================================================== #
#  KNOWLEDGE BASE                                                            #
# ========================================================================== #


@app.get("/api/knowledge-base", response_model=KnowledgeBaseInfo)
async def knowledge_base_info():
    """Return metadata about the indexed knowledge base."""
    doc_count = 0
    if search_service:
        try:
            doc_count = search_service.get_document_count()
        except Exception:
            pass

    # Count local files
    local_files: list[str] = []
    if KNOWLEDGE_BASE_DIR.exists():
        local_files = [
            f.name for f in KNOWLEDGE_BASE_DIR.iterdir()
            if f.suffix.lower() in (".docx", ".doc", ".pdf", ".txt")
        ]

    return KnowledgeBaseInfo(
        total_documents=doc_count,
        documents=[{"name": f} for f in local_files[:50]],
        index_status="connected" if search_service else "disconnected",
    )


@app.post("/api/knowledge-base/reindex")
async def reindex_knowledge_base():
    """Trigger re-indexing of all knowledge base documents."""
    if not search_service or not ingestion_agent:
        raise HTTPException(status_code=503, detail="Search or ingestion service unavailable")

    from src.indexing.reindex import index_all_documents
    result = await index_all_documents(
        kb_dir=str(KNOWLEDGE_BASE_DIR),
        search_service=search_service,
        ingestion_agent=ingestion_agent,
    )
    return result


# ========================================================================== #
#  DOCUMENT UPLOAD                                                           #
# ========================================================================== #


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a new HR policy document."""
    if not ingestion_agent:
        raise HTTPException(status_code=503, detail="Ingestion service unavailable")

    allowed = {".docx", ".doc", ".pdf", ".txt"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    save_path = KNOWLEDGE_BASE_DIR / (file.filename or "uploaded_doc" + ext)
    content = await file.read()
    save_path.write_bytes(content)

    # Process and index
    metadata = ingestion_agent.process_document(str(save_path))

    if search_service and metadata:
        search_service.upload_documents([metadata])

    return {"status": "ok", "file": file.filename, "metadata": metadata}


# ========================================================================== #
#  GLOSSARY                                                                  #
# ========================================================================== #


@app.get("/api/glossary")
async def glossary():
    """Return the HR vernacular-to-formal term glossary."""
    return {
        "glossary": [
            {"vernacular": k, "formal": v} for k, v in HR_GLOSSARY.items()
        ],
        "total": len(HR_GLOSSARY),
    }


# ========================================================================== #
#  AZURE STATUS                                                              #
# ========================================================================== #


@app.get("/api/azure/status")
async def azure_status():
    """Return configuration status of each Azure service."""
    return {
        "ai_foundry": {
            "endpoint": bool(os.getenv("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")),
        },
        "ai_search": {
            "endpoint": bool(os.getenv("AZURE_AI_SEARCH_ENDPOINT")),
            "index": os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "hr-policy-index"),
        },
        "document_intelligence": {
            "endpoint": bool(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")),
        },
        "openai": {
            "endpoint": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", ""),
        },
    }


# ========================================================================== #
#  COPILOT STUDIO                                                            #
# ========================================================================== #


@app.get("/api/copilot-studio/token")
async def copilot_studio_token():
    """Get a Direct Line token for Copilot Studio Web Chat embed."""
    if not copilot_studio:
        raise HTTPException(status_code=503, detail="Copilot Studio service not configured")
    token_data = await copilot_studio.get_directline_token()
    return token_data


@app.post("/api/copilot-studio/chat")
async def copilot_studio_chat(request: ChatRequest):
    """Send a message to Copilot Studio and return the response."""
    if not copilot_studio:
        raise HTTPException(status_code=503, detail="Copilot Studio service not configured")

    start = time.time()

    # Start conversation and send message
    conv = await copilot_studio.start_conversation()
    conversation_id = conv["conversationId"]

    token_data = await copilot_studio.get_directline_token()
    result = await copilot_studio.send_message(
        conversation_id=conversation_id,
        token=token_data["token"],
        message=request.message,
    )

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "answer": result.get("answer", "No response from Copilot Studio agent."),
        "source": "copilot_studio",
        "conversation_id": conversation_id,
        "processing_time_ms": elapsed_ms,
    }


@app.get("/api/copilot-studio/config")
async def copilot_studio_config():
    """Return safe-to-expose Copilot Studio configuration."""
    if not copilot_studio:
        return {"configured": False}
    config = copilot_studio.get_config()
    return {"configured": True, **config}


# ========================================================================== #
#  MAIN                                                                      #
# ========================================================================== #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
