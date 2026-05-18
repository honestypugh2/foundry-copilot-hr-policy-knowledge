"""
Knowledge Base Indexing Script  (chunked variant)

.. deprecated::
    Use ``scripts/index_knowledge_base_docintel_chunking.py`` (Pattern 1, Option 1)
    which adds synonym maps, semantic config, shared search_config.json, and larger
    chunk sizes (2000/200 vs 500/50).

Processes all Word documents in data/knowledge_base/ASK HR Knowledge/,
splits each document into fixed-size chunks via chunking.py, generates
a per-chunk embedding, and uploads chunk records to Azure AI Search.

Usage:
    python -m src.scripts.index_knowledge_base_chunking
    python -m src.scripts.index_knowledge_base_chunking --local-only
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from datetime import datetime, timezone

from src.document_processing.chunking import fixed_size_chunking
from src.document_processing.document_ingestion import (
    DocumentIngestionAgent,
    categorize_policy,
    extract_policy_number,
    generate_document_id,
)
from src.search.search_service import HRPolicySearchService, HR_GLOSSARY, enrich_content_with_glossary

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge"
SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf", ".txt"}

# Chunking defaults
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


async def index_all_documents(
    kb_dir: str | None = None,
    search_service: HRPolicySearchService | None = None,
    ingestion_agent: DocumentIngestionAgent | None = None,
    local_only: bool = False,
) -> dict:
    """
    Process every supported file in the knowledge base directory,
    chunk each document, and upload chunk records to Azure AI Search.

    Returns summary statistics.
    """
    kb_path = Path(kb_dir) if kb_dir else KNOWLEDGE_BASE_DIR
    if not kb_path.exists():
        logger.error(f"Knowledge base directory not found: {kb_path}")
        return {"error": f"Directory not found: {kb_path}"}

    # Initialise services
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
    total_chunks = 0
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

                # Split into fixed-size chunks
                chunks = fixed_size_chunking(
                    enriched_text,
                    size=CHUNK_SIZE,
                    overlap=CHUNK_OVERLAP,
                    document_id=doc_id,
                )

                for chunk in chunks:
                    # Generate per-chunk embedding
                    content_vector = None
                    if search_service:
                        content_vector = search_service.generate_embedding(
                            chunk.text[:8000]
                        )

                    doc = {
                        "id": chunk.chunk_id,
                        "title": title,
                        "policy_number": policy_number,
                        "category": category,
                        "content": chunk.text,
                        "chunk_index": chunk.chunk_index,
                        "parent_document_id": doc_id,
                        "file_path": str(filepath),
                        "file_type": filepath.suffix.lower(),
                        "word_count": len(chunk.text.split()),
                        "indexed_date": datetime.now(timezone.utc).isoformat(),
                        "source": "knowledge_base",
                    }
                    if content_vector:
                        doc["content_vector"] = content_vector

                    batch.append(doc)

                total_chunks += len(chunks)
                processed.append(filepath.name)
                logger.info(
                    f"  ✓ {title} — {len(chunks)} chunks from"
                    f" {result.get('word_count', 0)} words"
                )
            else:
                failed.append({"file": filepath.name, "error": "No content extracted"})
                logger.warning(f"  ✗ No content extracted from {filepath.name}")
        except Exception as e:
            failed.append({"file": filepath.name, "error": str(e)})
            logger.error(f"  ✗ Failed: {filepath.name} — {e}")

        # Upload in batches of 50 chunk docs
        if search_service and len(batch) >= 50:
            search_service.upload_documents(batch)
            logger.info(f"  Uploaded batch of {len(batch)} chunk documents")
            batch = []

    # Upload remaining
    if search_service and batch:
        search_service.upload_documents(batch)
        logger.info(f"Uploaded final batch of {len(batch)} chunk documents")

    total_indexed = search_service.get_document_count() if search_service else 0

    summary = {
        "total_files": len(files),
        "processed": len(processed),
        "failed": len(failed),
        "total_chunks": total_chunks,
        "indexed": total_indexed,
        "processed_files": processed,
        "failed_files": failed,
    }

    logger.info("=" * 60)
    logger.info(
        f"Indexing complete: {len(processed)}/{len(files)} files processed"
        f" → {total_chunks} chunks, {len(failed)} failed"
    )
    if search_service:
        logger.info(f"Total documents in index: {total_indexed}")
    logger.info("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Index HR knowledge base documents (chunked)"
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Process documents locally without Azure services",
    )
    parser.add_argument(
        "--kb-dir",
        type=str,
        default=None,
        help="Override knowledge base directory path",
    )
    args = parser.parse_args()

    result = asyncio.run(index_all_documents(
        kb_dir=args.kb_dir,
        local_only=args.local_only,
    ))

    if result.get("failed"):
        logger.warning("Failed files:")
        for f in result["failed"]:
            logger.warning(f"  - {f['file']}: {f['error']}")


if __name__ == "__main__":
    main()
