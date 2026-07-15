"""Knowledge-base reindexing for the backend ``/api/knowledge-base/reindex`` endpoint.

Relocated from the former ``scripts/index_knowledge_base.py`` so the runtime path
no longer depends on a (now removed) CLI script. Walks the knowledge base
directory, ingests each document, enriches content with glossary terms,
generates embeddings, and uploads to the Azure AI Search index via
``HRPolicySearchService``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from src.document_processing.document_ingestion import (
    DocumentIngestionAgent,
    categorize_policy,
    extract_policy_number,
    generate_document_id,
)
from src.search.search_service import (
    HRPolicySearchService,
    enrich_content_with_glossary,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge"
SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf", ".txt"}


async def index_all_documents(
    kb_dir: str | None = None,
    search_service: HRPolicySearchService | None = None,
    ingestion_agent: DocumentIngestionAgent | None = None,
    local_only: bool = False,
) -> dict:
    """
    Process every supported file in the knowledge base directory and
    upload the results to Azure AI Search.

    Returns summary statistics.
    """
    kb_path = Path(kb_dir) if kb_dir else KNOWLEDGE_BASE_DIR
    if not kb_path.exists():
        logger.error(f"Knowledge base directory not found: {kb_path}")
        return {"error": f"Directory not found: {kb_path}"}

    # Initialize services
    if ingestion_agent is None:
        ingestion_agent = DocumentIngestionAgent(use_azure=not local_only)
    if search_service is None and not local_only:
        search_service = HRPolicySearchService()

    # Create/ensure index exists
    if search_service:
        try:
            search_service.create_index()
            logger.info("Search index ready")
        except Exception as e:
            logger.warning(f"Could not create search index: {e}")

    # Discover documents
    files = [
        f for f in kb_path.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~")
    ]
    logger.info(f"Found {len(files)} documents in {kb_path}")

    processed = []
    failed = []
    batch: list[dict] = []

    for i, filepath in enumerate(sorted(files), 1):
        logger.info(f"[{i}/{len(files)}] Processing: {filepath.name}")
        try:
            result = ingestion_agent.process_document(str(filepath))
            text = result.get("text", "") if result else ""
            if result and text.strip():
                title = filepath.stem  # filename without extension
                doc_id = generate_document_id(str(filepath))
                policy_number = extract_policy_number(filepath.name)
                category = categorize_policy(filepath.name)

                # Enrich content with glossary terms so vernacular searches
                # work even when the consumer doesn't use synonym maps
                enriched_text = enrich_content_with_glossary(text, title=title)

                # Generate embedding vector if search service supports it
                content_vector = None
                if search_service:
                    content_vector = search_service.generate_embedding(enriched_text[:8000])

                doc = {
                    "id": doc_id,
                    "title": title,
                    "policy_number": policy_number,
                    "category": category,
                    "content": enriched_text,
                    "file_path": str(filepath),
                    "file_type": filepath.suffix.lower(),
                    "word_count": result.get("word_count", 0),
                    "indexed_date": datetime.now(timezone.utc).isoformat(),
                    "source": "knowledge_base",
                }
                if content_vector:
                    doc["content_vector"] = content_vector

                batch.append(doc)
                processed.append(filepath.name)
                logger.info(f"  ✓ {title} — {result.get('word_count', 0)} words")
            else:
                failed.append({"file": filepath.name, "error": "No content extracted"})
                logger.warning(f"  ✗ No content extracted from {filepath.name}")
        except Exception as e:
            failed.append({"file": filepath.name, "error": str(e)})
            logger.error(f"  ✗ Failed: {filepath.name} — {e}")

        # Upload in batches of 50
        if search_service and len(batch) >= 50:
            search_service.upload_documents(batch)
            logger.info(f"  Uploaded batch of {len(batch)} documents")
            batch = []

    # Upload remaining
    if search_service and batch:
        search_service.upload_documents(batch)
        logger.info(f"Uploaded final batch of {len(batch)} documents")

    total_indexed = search_service.get_document_count() if search_service else 0

    summary = {
        "total_files": len(files),
        "processed": len(processed),
        "failed": len(failed),
        "indexed": total_indexed,
        "processed_files": processed,
        "failed_files": failed,
    }

    logger.info("=" * 60)
    logger.info(f"Indexing complete: {len(processed)}/{len(files)} processed, {len(failed)} failed")
    if search_service:
        logger.info(f"Total documents in index: {total_indexed}")
    logger.info("=" * 60)

    return summary
