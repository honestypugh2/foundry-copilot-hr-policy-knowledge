#!/usr/bin/env python3
"""
Pattern 1 — Option 2: Integrated Vectorization with Document Intelligence Layout Skill

Server-side preprocessing pipeline for Copilot Studio → Azure AI Search (Knowledge Source direct).

Workflow:
    1. Upload HR policy documents to Azure Blob Storage
    2. Create Azure AI Search index with parent-child schema
    3. Create skillset with Document Intelligence Layout Skill + Embedding Skill
    4. Create indexer that connects blob data source → skillset → index
    5. The indexer automatically processes documents:
       - Document Intelligence Layout Skill extracts + chunks by document structure
       - AzureOpenAIEmbeddingSkill generates vectors for each chunk
       - Index projections map parent-child relationships
    6. Copilot Studio consumes the index as a Knowledge Source

Advantages over Option 1:
    - Structure-aware chunking (respects headings, paragraphs, tables)
    - Automatic reprocessing when source documents change
    - No client-side embedding generation needed
    - Built-in parent-child index projections

Shared configuration: src/config/search_config.json
    - Same index schema, synonym map, and semantic config as Option 1 and Pattern 2

Usage:
    python scripts/index_knowledge_base_integrated_vectorization.py
    python scripts/index_knowledge_base_integrated_vectorization.py --upload-only
    python scripts/index_knowledge_base_integrated_vectorization.py --create-pipeline-only

References:
    - Document Layout skill: https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-document-intelligence-layout
    - Semantic chunking: https://learn.microsoft.com/en-us/azure/search/search-how-to-semantic-chunking
    - Index projections: https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.search_config import search_cfg

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
    from azure.search.documents.indexes.models import (
        AzureOpenAIVectorizer,
        AzureOpenAIVectorizerParameters,
        HnswAlgorithmConfiguration,
        HnswParameters,
        InputFieldMappingEntry,
        OutputFieldMappingEntry,
        ScalarQuantizationCompression,
        ScalarQuantizationParameters,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SearchableField,
        SearchIndexer,
        SearchIndexerDataContainer,
        SearchIndexerDataSourceConnection,
        SearchIndexerIndexProjectionSelector,
        SearchIndexerIndexProjection,
        SearchIndexerIndexProjectionsParameters,
        SearchIndexerSkillset,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        SynonymMap,
        VectorSearch,
        VectorSearchProfile,
        IndexingParameters,
        IndexingParametersConfiguration,
        FieldMapping,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    logger.warning("azure-search-documents not installed")

try:
    from azure.storage.blob import BlobServiceClient
    BLOB_SDK_AVAILABLE = True
except ImportError:
    BLOB_SDK_AVAILABLE = False
    logger.warning("azure-storage-blob not installed")


# ---------------------------------------------------------------------------
# Config from search_config.json
# ---------------------------------------------------------------------------
INDEX_NAME = search_cfg.index_name
CONTAINER_NAME = search_cfg.blob_container_name
SKILLSET_CFG = search_cfg.document_layout_skillset
VECTOR_CFG = search_cfg.vector_search
SEMANTIC_CFG = search_cfg.semantic_search
SYNONYM_CFG_NAME = search_cfg.synonym_map_name
SYNONYM_CFG_FIELDS = search_cfg.synonym_map_fields

# Naming conventions
DATA_SOURCE_NAME = search_cfg.indexer_data_source_name
SKILLSET_NAME = SKILLSET_CFG.get("name", "hr-policy-doc-layout-skillset")
INDEXER_NAME = search_cfg.indexer_name


def _get_credential():
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    if search_key and not search_key.startswith("your_"):
        return AzureKeyCredential(search_key)
    try:
        return AzureCliCredential()
    except Exception:
        return DefaultAzureCredential()


def upload_documents(data_dir: str) -> int:
    """Upload HR policy documents to Azure Blob Storage."""
    if not BLOB_SDK_AVAILABLE:
        logger.error("azure-storage-blob not installed")
        return 0

    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")

    if conn_str:
        blob_service = BlobServiceClient.from_connection_string(conn_str)
    elif account_url:
        try:
            cred = AzureCliCredential()
        except Exception:
            cred = DefaultAzureCredential()
        blob_service = BlobServiceClient(account_url=account_url, credential=cred)
    else:
        logger.error("Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL")
        return 0

    container_client = blob_service.get_container_client(CONTAINER_NAME)
    try:
        container_client.create_container()
        logger.info("Created container '%s'", CONTAINER_NAME)
    except Exception:
        pass  # Container already exists

    data_path = Path(data_dir)
    uploaded = 0
    extensions = {ext.lower() for ext in search_cfg.included_extensions}

    for file_path in sorted(data_path.rglob("*")):
        if file_path.suffix.lower() not in extensions:
            continue

        # Check excluded extensions from config
        excluded = SKILLSET_CFG.get("excluded_extensions", [])
        if file_path.suffix.lower() in excluded:
            continue

        blob_name = file_path.name
        logger.info("  Uploading: %s", blob_name)
        with open(file_path, "rb") as f:
            container_client.upload_blob(name=blob_name, data=f, overwrite=True)
        uploaded += 1

    logger.info("Uploaded %d documents to container '%s'", uploaded, CONTAINER_NAME)
    return uploaded


def create_synonym_map() -> None:
    """Create HR glossary synonym map."""
    from src.search.search_service import HR_GLOSSARY

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=_get_credential())

    grouped: dict[str, list[str]] = {}
    for vernacular, formal in HR_GLOSSARY.items():
        grouped.setdefault(formal, []).append(vernacular)

    rules = []
    for formal, vernaculars in grouped.items():
        all_terms = vernaculars + [formal]
        rules.append(",".join(all_terms))

    synonym_map = SynonymMap(name=SYNONYM_CFG_NAME, synonyms=rules)
    index_client.create_or_update_synonym_map(synonym_map)
    logger.info("Synonym map '%s' created with %d rules", SYNONYM_CFG_NAME, len(rules))


def create_index() -> None:
    """Create search index with parent-child schema for Document Layout skill output."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=_get_credential())

    # Vector search configuration
    algo_cfg = VECTOR_CFG.get("algorithm", {})
    algo_params = algo_cfg.get("parameters", {})
    compression_cfg = VECTOR_CFG.get("compression", {})
    compression_params = compression_cfg.get("parameters", {})
    profile_cfg = VECTOR_CFG.get("profile", {})
    vectorizer_cfg = VECTOR_CFG.get("vectorizer", {})

    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    if "/openai" in aoai_endpoint:
        aoai_endpoint = aoai_endpoint.split("/openai")[0]

    vector_search = VectorSearch(
        algorithms=[  # type: ignore[arg-type]
            HnswAlgorithmConfiguration(
                name=algo_cfg.get("name", "hr-hnsw-config"),
                parameters=HnswParameters(
                    metric=algo_params.get("metric", "cosine"),
                    m=algo_params.get("m", 4),
                    ef_construction=algo_params.get("efConstruction", 400),
                    ef_search=algo_params.get("efSearch", 500),
                ),
            )
        ],
        compressions=[  # type: ignore[arg-type]
            ScalarQuantizationCompression(
                compression_name=compression_cfg.get("name", "hr-scalar-quantization"),
                parameters=ScalarQuantizationParameters(
                    quantized_data_type=compression_params.get("quantized_data_type", "int8"),
                ),
            )
        ],
        vectorizers=[  # type: ignore[arg-type]
            AzureOpenAIVectorizer(
                vectorizer_name=vectorizer_cfg.get("name", "hr-azure-openai-vectorizer"),
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=aoai_endpoint,
                    deployment_name=search_cfg.embedding_deployment,
                    model_name=search_cfg.embedding_model,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=profile_cfg.get("name", "hr-vector-profile"),
                algorithm_configuration_name=algo_cfg.get("name", "hr-hnsw-config"),
                compression_name=compression_cfg.get("name", "hr-scalar-quantization"),
                vectorizer_name=vectorizer_cfg.get("name", "hr-azure-openai-vectorizer"),
            )
        ],
    )

    # Semantic search
    sem_cfg = SEMANTIC_CFG.get("prioritized_fields", {})
    semantic_search = SemanticSearch(
        default_configuration_name=search_cfg.semantic_configuration,
        configurations=[
            SemanticConfiguration(
                name=search_cfg.semantic_configuration,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name=sem_cfg.get("title_field", "parent_title")),
                    content_fields=[
                        SemanticField(field_name=f) for f in sem_cfg.get("content_fields", ["policy"])
                    ],
                    keywords_fields=[
                        SemanticField(field_name=f) for f in sem_cfg.get("keywords_fields", [])
                    ] or None,
                ),
            )
        ],
    )

    # Fields — parent-child schema
    synonym_fields = set(SYNONYM_CFG_FIELDS)

    def _searchable(name: str, **kwargs):
        if name in synonym_fields:
            kwargs["synonym_map_names"] = [SYNONYM_CFG_NAME]
        return SearchableField(name=name, type=SearchFieldDataType.String, **kwargs)

    fields = [
        SearchField(
            name="id", type=SearchFieldDataType.String,
            key=True, filterable=True, analyzer_name="keyword",
        ),
        SimpleField(name=search_cfg.blob_url_field, type="Edm.String"),
        _searchable(search_cfg.content_field),
        _searchable(search_cfg.source_field),
        _searchable(search_cfg.filename_field, filterable=True),
        _searchable(search_cfg.filepath_field, filterable=True),
        _searchable(search_cfg.parent_title_field, filterable=True),
        _searchable(search_cfg.policy_number_field, filterable=True),
        SimpleField(
            name=search_cfg.parent_key_field,
            type="Edm.String", filterable=True,
        ),
        SearchField(
            name=search_cfg.vector_field,
            type="Collection(Edm.Single)",
            searchable=True,
            vector_search_dimensions=search_cfg.embedding_dimensions,
            vector_search_profile_name=profile_cfg.get("name", "hr-vector-profile"),
        ),
    ]

    index = SearchIndex(
        name=INDEX_NAME, fields=fields,
        vector_search=vector_search, semantic_search=semantic_search,
    )

    index_client.create_or_update_index(index)
    logger.info("Index '%s' created with Document Layout schema", INDEX_NAME)


def create_data_source() -> None:
    """Create Azure Blob Storage data source connection."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

    indexer_client = SearchIndexerClient(
        endpoint=search_endpoint, credential=_get_credential()
    )

    data_source = SearchIndexerDataSourceConnection(
        name=DATA_SOURCE_NAME,
        type="azureblob",
        connection_string=conn_str,
        container=SearchIndexerDataContainer(name=CONTAINER_NAME),
    )

    indexer_client.create_or_update_data_source_connection(data_source)
    logger.info("Data source '%s' created for container '%s'", DATA_SOURCE_NAME, CONTAINER_NAME)


def create_skillset() -> None:
    """Create skillset with Document Intelligence Layout Skill + Embedding Skill.

    Pipeline:
        Document → DocumentIntelligenceLayoutSkill (structure-aware chunking)
                 → AzureOpenAIEmbeddingSkill (vectorization per chunk)
                 → Index projections (parent-child mapping)
    """
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    aoai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    cognitive_key = os.getenv("AZURE_AI_SERVICES_KEY", "")

    if "/openai" in aoai_endpoint:
        aoai_endpoint = aoai_endpoint.split("/openai")[0]

    indexer_client = SearchIndexerClient(
        endpoint=search_endpoint, credential=_get_credential()
    )

    # Get skill config (embedding settings come from the single `embedding` block)
    layout_skill_cfg = None
    for skill in SKILLSET_CFG.get("skills", []):
        if skill.get("type") == "DocumentIntelligenceLayoutSkill":
            layout_skill_cfg = skill
            break

    # Build REST-compatible skillset definition
    # The DocumentIntelligenceLayoutSkill uses @odata.type for SDK compatibility
    chunking_props = layout_skill_cfg.get("chunking_properties", {}) if layout_skill_cfg else {}

    skills = []

    # Skill 1: Document Intelligence Layout
    skills.append({
        "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
        "name": layout_skill_cfg.get("name", "document-intelligence-layout") if layout_skill_cfg else "document-intelligence-layout",
        "description": "Analyze document structure using Azure Document Intelligence",
        "context": "/document",
        "outputMode": "oneToMany",
        "outputFormat": layout_skill_cfg.get("output_format", "text") if layout_skill_cfg else "text",
        "markdownHeaderDepth": layout_skill_cfg.get("markdown_header_depth", "h3") if layout_skill_cfg else "h3",
        "chunkingProperties": {
            "unit": chunking_props.get("unit", "characters"),
            "maximumLength": chunking_props.get("maximum_length", 2000),
            "overlapLength": chunking_props.get("overlap_length", 200),
        },
        "inputs": [
            {"name": "file_data", "source": "/document/file_data"}
        ],
        "outputs": [
            {"name": "text_sections", "targetName": "text_sections"}
        ],
    })

    # Skill 2: Azure OpenAI Embedding (settings from the single `embedding` block)
    emb_deployment = search_cfg.embedding_deployment
    emb_model = search_cfg.embedding_model
    emb_dimensions = search_cfg.embedding_dimensions

    skills.append({
        "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
        "name": "azure-openai-embedding",
        "description": "Generate embeddings for each text chunk",
        "context": "/document/text_sections/*",
        "inputs": [
            {"name": "text", "source": "/document/text_sections/*/content"}
        ],
        "outputs": [
            {"name": "embedding", "targetName": "text_vector"}
        ],
        "resourceUri": aoai_endpoint,
        "deploymentId": emb_deployment,
        "modelName": emb_model,
        "dimensions": emb_dimensions,
        "apiKey": aoai_key if aoai_key and not aoai_key.startswith("your_") else None,
    })

    # Index projections (parent-child)
    proj_cfg = SKILLSET_CFG.get("index_projections", {})
    index_projections = {
        "selectors": [{
            "targetIndexName": proj_cfg.get("target_index_name", INDEX_NAME),
            "parentKeyFieldName": proj_cfg.get("parent_key_field_name", search_cfg.parent_key_field),
            "sourceContext": proj_cfg.get("source_context", "/document/text_sections/*"),
            "mappings": proj_cfg.get("mappings", []),
        }],
        "parameters": {
            "projectionMode": "skipIndexingParentDocuments"
        },
    }

    # Cognitive services for billing
    cognitive_services = None
    if cognitive_key and not cognitive_key.startswith("your_"):
        cognitive_services = {
            "@odata.type": "#Microsoft.Azure.Search.CognitiveServicesByKey",
            "key": cognitive_key,
        }

    # Build skillset payload
    skillset_payload = {
        "name": SKILLSET_NAME,
        "description": SKILLSET_CFG.get("description", "Document Layout + Embedding skillset"),
        "skills": skills,
        "indexProjections": index_projections,
    }
    if cognitive_services:
        skillset_payload["cognitiveServices"] = cognitive_services

    # Use REST API to create skillset (SDK may not support all skill types natively)
    import requests
    api_version = search_cfg.indexer_api_version
    api_key = os.getenv("AZURE_SEARCH_API_KEY", "")

    headers = {"Content-Type": "application/json"}
    if api_key and not api_key.startswith("your_"):
        headers["api-key"] = api_key
    else:
        from azure.identity import DefaultAzureCredential
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        headers["Authorization"] = f"Bearer {token}"

    url = f"{search_endpoint}/skillsets/{SKILLSET_NAME}?api-version={api_version}"
    resp = requests.put(url, json=skillset_payload, headers=headers)

    if resp.status_code in (200, 201):
        logger.info("Skillset '%s' created with Document Layout + Embedding skills", SKILLSET_NAME)
    else:
        logger.error("Skillset creation failed (%d): %s", resp.status_code, resp.text)


def create_indexer() -> None:
    """Create indexer that connects data source → skillset → index."""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    indexer_client = SearchIndexerClient(
        endpoint=search_endpoint, credential=_get_credential()
    )

    indexer = SearchIndexer(
        name=INDEXER_NAME,
        data_source_name=DATA_SOURCE_NAME,
        target_index_name=INDEX_NAME,
        skillset_name=SKILLSET_NAME,
        parameters=IndexingParameters(
            batch_size=search_cfg.indexer_batch_size,
            configuration=IndexingParametersConfiguration(
                data_to_extract=search_cfg.indexer_data_to_extract,
                parsing_mode=search_cfg.indexer_parsing_mode,
                allow_skillset_to_read_file_data=search_cfg.indexer_allow_skillset_to_read_file_data,
            ),
        ),
        field_mappings=[
            FieldMapping(source_field_name=fm["source"], target_field_name=fm["target"])
            for fm in search_cfg.indexer_field_mappings
        ],
        output_field_mappings=[],
    )

    indexer_client.create_or_update_indexer(indexer)
    logger.info("Indexer '%s' created → will run automatically", INDEXER_NAME)


def run(data_dir: str, upload_only: bool = False, create_pipeline_only: bool = False) -> None:
    """Execute the full integrated vectorization setup."""

    if not SDK_AVAILABLE:
        logger.error("azure-search-documents SDK not installed")
        return

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if not search_endpoint:
        logger.error("AZURE_SEARCH_ENDPOINT not set")
        return

    if not create_pipeline_only:
        # Upload documents to blob
        logger.info("=== Step 1: Upload documents to Blob Storage ===")
        count = upload_documents(data_dir)
        if count == 0:
            logger.warning("No documents uploaded")
        if upload_only:
            return

    # Create search pipeline
    logger.info("=== Step 2: Create synonym map ===")
    create_synonym_map()

    logger.info("=== Step 3: Create search index ===")
    create_index()

    logger.info("=== Step 4: Create blob data source ===")
    create_data_source()

    logger.info("=== Step 5: Create skillset (Document Layout + Embedding) ===")
    create_skillset()

    logger.info("=== Step 6: Create and run indexer ===")
    create_indexer()

    logger.info("")
    logger.info("Pipeline created successfully!")
    logger.info("  Data source: %s", DATA_SOURCE_NAME)
    logger.info("  Skillset:    %s (DocumentIntelligenceLayoutSkill + AzureOpenAIEmbeddingSkill)", SKILLSET_NAME)
    logger.info("  Index:       %s", INDEX_NAME)
    logger.info("  Indexer:     %s", INDEXER_NAME)
    logger.info("")
    logger.info("The indexer will run automatically and process documents.")
    logger.info("Monitor progress in Azure Portal → AI Search → Indexers.")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. In Copilot Studio, add Azure AI Search as a Knowledge Source")
    logger.info("  2. Point to index '%s' with semantic config '%s'",
                INDEX_NAME, search_cfg.semantic_configuration)
    logger.info("  3. Enable generative orchestration for grounded answers")
    logger.info("  4. Documents will auto-reindex when updated in blob storage")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pattern 1 Option 2: Integrated Vectorization with Document Layout Skill"
    )
    parser.add_argument(
        "--data-dir",
        default=str(PROJECT_ROOT / "data" / "knowledge_base" / "ASK HR Knowledge"),
        help="Path to HR policy documents",
    )
    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Only upload documents to blob storage",
    )
    parser.add_argument(
        "--create-pipeline-only",
        action="store_true",
        help="Only create index/skillset/indexer (skip upload)",
    )
    args = parser.parse_args()
    run(args.data_dir, args.upload_only, args.create_pipeline_only)
