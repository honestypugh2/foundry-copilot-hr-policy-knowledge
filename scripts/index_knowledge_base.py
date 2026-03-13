"""
Knowledge Base Indexing Script

Processes all Word documents in data/knowledge_base/ASK HR Knowledge/ and
uploads them to Azure AI Search for the HR Policy Agent.

Usage:
    python -m scripts.index_knowledge_base
    python -m scripts.index_knowledge_base --local-only
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from datetime import datetime, timezone

from src.document_processing.document_ingestion import (
    DocumentIngestionAgent,
    categorize_policy,
    extract_policy_number,
    generate_document_id,
)
from src.search.search_service import HRPolicySearchService, HR_GLOSSARY

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge"
SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf", ".txt"}


def enrich_content_with_glossary(title: str, content: str) -> str:
    """Append matching glossary vernacular/formal terms to document content.

    This ensures that common shorthand (e.g. "BBP", "PTO", "STD") appears
    directly in the searchable text so any consumer — including Copilot Studio,
    which may not trigger synonym maps — can find the document.
    """
    combined = (title + " " + content).lower()
    matched_terms: set[str] = set()

    for vernacular, formal in HR_GLOSSARY.items():
        # If the document already mentions the formal term, add the vernacular aliases
        if formal.lower() in combined:
            matched_terms.add(vernacular)
            matched_terms.add(formal)
        # If the document already mentions the vernacular, add the formal term
        if vernacular in combined:
            matched_terms.add(vernacular)
            matched_terms.add(formal)

    if not matched_terms:
        return content

    # Build a glossary footer that is searchable but clearly separated
    glossary_footer = (
        "\n\n---\nRelated terms: "
        + ", ".join(sorted(matched_terms))
    )
    return content + glossary_footer


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
                enriched_text = enrich_content_with_glossary(title, text)

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


def main():
    parser = argparse.ArgumentParser(description="Index HR knowledge base documents")
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
    parser.add_argument(
        "--test-ingestion",
        action="store_true",
        help="Test Document Intelligence ingestion only (no search upload)",
    )
    args = parser.parse_args()

    if args.test_ingestion:
        test_ingestion_only(kb_dir=args.kb_dir)
    else:
        result = asyncio.run(index_all_documents(
            kb_dir=args.kb_dir,
            local_only=args.local_only,
        ))

        if result.get("failed"):
            logger.warning("Failed files:")
            for f in result["failed"]:
                logger.warning(f"  - {f['file']}: {f['error']}")


def test_ingestion_only(kb_dir: str | None = None):
    """Test Document Intelligence client by processing all documents without uploading to search."""
    kb_path = Path(kb_dir) if kb_dir else KNOWLEDGE_BASE_DIR
    if not kb_path.exists():
        logger.error(f"Knowledge base directory not found: {kb_path}")
        sys.exit(1)

    agent = DocumentIngestionAgent(use_azure=True)
    files = sorted(
        f for f in kb_path.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~")
    )
    logger.info(f"Testing Document Intelligence ingestion on {len(files)} files")
    logger.info("=" * 60)

    processed = 0
    failed = 0
    for i, filepath in enumerate(files, 1):
        try:
            result = agent.process_document(str(filepath))
            method = result.get("extraction_method", "unknown")
            words = result.get("word_count", 0)
            pages = result.get("page_count", 0)
            logger.info(f"[{i}/{len(files)}] OK  {filepath.name}  ({method}, {pages} pages, {words} words)")
            processed += 1
        except Exception as e:
            logger.error(f"[{i}/{len(files)}] FAIL {filepath.name}  — {e}")
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Done: {processed} processed, {failed} failed out of {len(files)} files")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
