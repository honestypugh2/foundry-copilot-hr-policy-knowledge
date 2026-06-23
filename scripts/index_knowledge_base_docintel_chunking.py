#!/usr/bin/env python3
"""
Pattern 1 — Option 1: Document Intelligence + Client-Side Chunking + Push to Azure AI Search

Preprocessing pipeline for Copilot Studio → Azure AI Search (Knowledge Source direct).

Workflow:
    1. Read HR policy documents from data/knowledge_base/
    2. Extract text using Azure Document Intelligence (prebuilt-layout)
    3. Chunk with overlap using fixed-size chunking (parent-child)
    4. Generate embeddings via Azure OpenAI (text-embedding-3-small)
    5. Push chunked documents to Azure AI Search index (hr-policy-index)
    6. Create synonym map from HR glossary for vernacular expansion

The index is then consumed directly by Copilot Studio as a Knowledge Source
with vector + semantic ranking for grounded generative answers.

Shared configuration: src/config/search_config.json
    - Same index schema, synonym map, and semantic config as Option 2 and Pattern 2
    - Ensures consistent search behavior regardless of preprocessing pipeline

Usage:
    python scripts/index_knowledge_base_docintel_chunking.py
    python scripts/index_knowledge_base_docintel_chunking.py --local-only  # skip Azure DI
    python scripts/index_knowledge_base_docintel_chunking.py --data-dir data/knowledge_base_lab

Reference:
    - Parent-child chunking: https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.search_config import search_cfg
from src.document_processing.document_ingestion import DocumentIngestionAgent, extract_policy_number, categorize_policy
from src.document_processing.chunking import fixed_size_chunking
from src.search.search_service import HR_GLOSSARY, expand_query_with_glossary, enrich_content_with_glossary

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants from shared config
# ---------------------------------------------------------------------------
INDEX_NAME = search_cfg.index_name
CONTENT_FIELD = search_cfg.content_field
SOURCE_FIELD = search_cfg.source_field
VECTOR_FIELD = search_cfg.vector_field
PARENT_KEY_FIELD = search_cfg.parent_key_field
PARENT_TITLE_FIELD = search_cfg.parent_title_field
POLICY_NUMBER_FIELD = search_cfg.policy_number_field
BLOB_URL_FIELD = search_cfg.blob_url_field

# Chunking parameters (match the skillset config)
CHUNK_SIZE = search_cfg.skillset.get("skills", [{}])[0].get("maximum_page_length", 2000)
CHUNK_OVERLAP = search_cfg.skillset.get("skills", [{}])[0].get("page_overlap_length", 200)


def generate_doc_id(file_path: str, chunk_index: int = 0) -> str:
    """Generate a deterministic document ID from file path + chunk index."""
    raw = f"{file_path}::chunk_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def run(data_dir: str, local_only: bool = False) -> None:
    """Execute the full preprocessing pipeline."""

    from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService

    # 1. Initialize services
    search_service = IntegratedVectorizationSearchService()
    ingestion_agent = DocumentIngestionAgent()

    if not local_only and not search_service.is_configured:
        logger.error("Azure AI Search not configured. Set AZURE_SEARCH_ENDPOINT.")
        return

    # 2. Create index + synonym map
    if not local_only:
        logger.info("Creating index '%s' with synonym maps and semantic config...", INDEX_NAME)
        search_service.create_synonym_map()
        search_service.create_index()

    # 3. Discover documents
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.error("Data directory not found: %s", data_dir)
        return

    doc_files = []
    for ext in ("*.docx", "*.doc", "*.pdf"):
        doc_files.extend(data_path.rglob(ext))

    logger.info("Found %d documents in %s", len(doc_files), data_dir)

    # 4. Process each document
    all_chunks = []
    for file_path in sorted(doc_files):
        logger.info("Processing: %s", file_path.name)

        # 4a. Extract text via Document Intelligence
        result = ingestion_agent.process_document(str(file_path))
        if not result or not result.get("text"):
            logger.warning("  Skipping (no text extracted): %s", file_path.name)
            continue

        raw_text = result["text"]
        policy_number = extract_policy_number(str(file_path))
        category = categorize_policy(str(file_path))
        parent_title = file_path.stem
        parent_id = generate_doc_id(str(file_path))

        logger.info("  Extracted %d words, policy=%s, category=%s",
                     result.get("word_count", 0), policy_number, category)

        # 4b. Chunk with overlap (parent-child pattern)
        chunks = fixed_size_chunking(raw_text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        logger.info("  Split into %d chunks (size=%d, overlap=%d)",
                     len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)

        for chunk in chunks:
            enriched = enrich_content_with_glossary(chunk.text)
            source_text = f"[Source: {parent_title} | Policy {policy_number}]\n{enriched}"

            doc = {
                "id": generate_doc_id(str(file_path), chunk.chunk_index),
                PARENT_KEY_FIELD: parent_id,
                PARENT_TITLE_FIELD: parent_title,
                POLICY_NUMBER_FIELD: policy_number or "",
                CONTENT_FIELD: enriched,
                SOURCE_FIELD: source_text,
                BLOB_URL_FIELD: "",
                "metadata_storage_name": file_path.name,
                "metadata_storage_path": str(file_path),
                "category": category,
            }
            all_chunks.append(doc)

    logger.info("Total chunks to index: %d", len(all_chunks))

    if local_only:
        logger.info("--local-only mode: skipping upload. %d chunks prepared.", len(all_chunks))
        return

    # 5. Generate embeddings and upload
    logger.info("Generating embeddings and uploading to '%s'...", INDEX_NAME)

    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]

        for doc in batch:
            embedding = search_service.generate_embedding(doc[CONTENT_FIELD])
            if embedding:
                doc[VECTOR_FIELD] = embedding

        # Upload batch
        try:
            client = search_service._get_search_client()
            result = client.upload_documents(batch)
            succeeded = sum(1 for r in result if r.succeeded)
            logger.info("  Uploaded batch %d-%d: %d/%d succeeded",
                        i, i + len(batch), succeeded, len(batch))
        except Exception as e:
            logger.error("  Upload failed for batch %d: %s", i, e)

    logger.info("Done. %d chunks indexed into '%s'.", len(all_chunks), INDEX_NAME)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. In Copilot Studio, add Azure AI Search as a Knowledge Source")
    logger.info("  2. Point to index '%s' with semantic config '%s'",
                INDEX_NAME, search_cfg.semantic_configuration)
    logger.info("  3. Enable generative orchestration for grounded answers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pattern 1 Option 1: DocIntel + Chunking → Azure AI Search → Copilot Studio"
    )
    parser.add_argument(
        "--data-dir",
        default=str(PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge"),
        help="Path to HR policy documents",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Extract and chunk locally without uploading to Azure",
    )
    args = parser.parse_args()
    run(args.data_dir, args.local_only)
