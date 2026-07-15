"""
Integrated Vectorization Search Client

Wraps the Azure AI Search SDK to provide hybrid search
(full-text + vector + semantic ranker) against an index populated
by the integrated-vectorization skillset pipeline
(SplitSkill → AzureOpenAIEmbeddingSkill).

Unlike the original HRPolicySearchService which pre-computes
embeddings client-side, this client relies on the Azure AI Search
indexer + skillset to handle chunking and vectorization at index
time, and an Azure OpenAI vectorizer for query-time embedding.

Both search services share the same search_config.json for consistent
field names, vector search, semantic search, and synonym map configuration.

Reference:
  https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import QueryType, VectorizedQuery
    SEARCH_SDK_AVAILABLE = True
except ImportError:
    SEARCH_SDK_AVAILABLE = False
    logger.warning("azure-search-documents not installed")

try:
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        AzureOpenAIVectorizer,
        AzureOpenAIVectorizerParameters,
        HnswAlgorithmConfiguration,
        HnswParameters,
        ScalarQuantizationCompression,
        ScalarQuantizationParameters,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SearchableField,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        SynonymMap,
        VectorSearch,
        VectorSearchProfile,
    )
    INDEX_SDK_AVAILABLE = True
except ImportError:
    INDEX_SDK_AVAILABLE = False
    logger.info("azure-search-documents index models not available")

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("openai not installed, vector search unavailable")

from src.config.search_config import search_cfg
from src.search.search_service import HR_GLOSSARY, expand_query_with_glossary


# ---------------------------------------------------------------------------
# Load search configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "search_config.json"
if _CONFIG_PATH.exists():
    with open(_CONFIG_PATH) as f:
        _FULL_CONFIG = json.load(f)
        _SEARCH_CONFIG = _FULL_CONFIG.get("search_config", {})
        _VECTOR_SEARCH_CONFIG = _FULL_CONFIG.get("vector_search", {})
        _SEMANTIC_SEARCH_CONFIG = _FULL_CONFIG.get("semantic_search", {})
        _SKILLSET_CONFIG = _FULL_CONFIG.get("skillset", {})
        _SYNONYM_MAP_CONFIG = _FULL_CONFIG.get("synonym_map", {})
else:
    _FULL_CONFIG = {}
    _SEARCH_CONFIG = {}
    _VECTOR_SEARCH_CONFIG = {}
    _SEMANTIC_SEARCH_CONFIG = {}
    _SKILLSET_CONFIG = {}
    _SYNONYM_MAP_CONFIG = {}


class IntegratedVectorizationSearchService:
    """
    Azure AI Search client for hybrid search against an index built with
    integrated vectorization (indexer + skillset pipeline).

    Architecture flow:
        Azure Blob Storage → Azure AI Search Indexer
            → Skillset (SplitSkill + AzureOpenAIEmbeddingSkill)
            → Search Index (chunked + vectorized)
            → Hybrid query (text + vector + semantic ranker)

    Key difference from HRPolicySearchService:
        - Indexing: No client-side embedding needed; the skillset handles
          chunking and embedding at index time.
        - Querying: The index's AzureOpenAIVectorizer converts text queries
          to vectors at query time, or embeddings can be generated client-side.
    """

    # Sourced from the single embedding block in search_config.json.
    EMBEDDING_MODEL = search_cfg.embedding_model
    EMBEDDING_DIMENSIONS = search_cfg.embedding_dimensions

    def __init__(self) -> None:
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        self.index_name = os.getenv(
            "AZURE_SEARCH_INDEX_NAME",
            _SEARCH_CONFIG.get("index_name", "hr-policy-index"),
        )
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.use_managed_identity = (
            os.getenv("USE_MANAGED_IDENTITY", "true").lower() == "true"
        )

        # Azure OpenAI for client-side embeddings (optional fallback)
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")

        # Lazy-init clients
        self._search_client: Optional[SearchClient] = None
        self._openai_client = None

        # Index field names from config
        self._vector_field = _SEARCH_CONFIG.get("vector_field", "policy_vector")
        self._content_field = _SEARCH_CONFIG.get("content_field", "policy")
        self._source_field = _SEARCH_CONFIG.get("source_field", "policy_with_source")
        self._blob_url_field = _SEARCH_CONFIG.get("blob_url_field", "blob_url")
        self._filename_field = _SEARCH_CONFIG.get("filename_field", "metadata_storage_name")
        self._filepath_field = _SEARCH_CONFIG.get("filepath_field", "metadata_storage_path")
        self._parent_title_field = _SEARCH_CONFIG.get("parent_title_field", "parent_title")
        self._policy_number_field = _SEARCH_CONFIG.get("policy_number_field", "policy_number")
        self._semantic_config = _SEARCH_CONFIG.get(
            "semantic_configuration", "hr-semantic-config"
        )
        self._top_k = _SEARCH_CONFIG.get("top_k", 5)

        # Synonym map config
        self._synonym_map_name = _SYNONYM_MAP_CONFIG.get("name", "hr-glossary-synonyms")
        self._synonym_map_fields = _SYNONYM_MAP_CONFIG.get("fields", [
            "parent_title", "policy", "policy_with_source",
        ])

    @property
    def is_configured(self) -> bool:
        return bool(self.search_endpoint) and SEARCH_SDK_AVAILABLE

    # ------------------------------------------------------------------
    # Field normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_policy_number(value: str) -> str:
        """Return *value* only if it looks like a numeric policy number."""
        return value if value and value.isdigit() else ""

    # ------------------------------------------------------------------
    # Credential helpers
    # ------------------------------------------------------------------

    def _get_credential(self):
        if self.search_key and not self.search_key.startswith("your_"):
            return AzureKeyCredential(self.search_key)
        if self.use_managed_identity:
            try:
                return AzureCliCredential()
            except Exception:
                return DefaultAzureCredential()
        raise ValueError("No valid credential for Azure AI Search")

    # ------------------------------------------------------------------
    # Client accessors
    # ------------------------------------------------------------------

    def _get_search_client(self) -> SearchClient:
        if self._search_client is None:
            if not SEARCH_SDK_AVAILABLE:
                raise RuntimeError("azure-search-documents SDK not installed")
            if not self.search_endpoint:
                raise RuntimeError("AZURE_SEARCH_ENDPOINT not set")
            self._search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.index_name,
                credential=self._get_credential(),
            )
        return self._search_client

    def _get_openai_client(self):
        if self._openai_client is None and OPENAI_AVAILABLE and self.openai_endpoint:
            if self.openai_key and not self.openai_key.startswith("your_"):
                self._openai_client = AzureOpenAI(
                    azure_endpoint=self.openai_endpoint,
                    api_version=self.openai_api_version,
                    api_key=self.openai_key,
                )
            else:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )
                self._openai_client = AzureOpenAI(
                    azure_endpoint=self.openai_endpoint,
                    api_version=self.openai_api_version,
                    azure_ad_token_provider=token_provider,
                )
        return self._openai_client

    # ------------------------------------------------------------------
    # Synonym map
    # ------------------------------------------------------------------

    def create_synonym_map(self) -> bool:
        """Create an Azure AI Search synonym map from the HR glossary.

        Uses the same HR_GLOSSARY as the legacy HRPolicySearchService to
        ensure consistent vernacular expansion at the index level.
        """
        if not INDEX_SDK_AVAILABLE:
            logger.error("azure-search-documents index models not available")
            return False

        if not self.search_endpoint:
            logger.error("AZURE_SEARCH_ENDPOINT not set")
            return False

        index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self._get_credential(),
        )

        # Build synonym rules in Solr format
        grouped: dict[str, list[str]] = {}
        for vernacular, formal in HR_GLOSSARY.items():
            grouped.setdefault(formal, []).append(vernacular)

        rules = []
        for formal, vernaculars in grouped.items():
            all_terms = vernaculars + [formal]
            rules.append(",".join(all_terms))

        synonym_map = SynonymMap(
            name=self._synonym_map_name,
            synonyms=rules,
        )

        try:
            index_client.create_or_update_synonym_map(synonym_map)
            logger.info(
                "Synonym map '%s' created/updated with %d rules",
                self._synonym_map_name, len(rules),
            )
            return True
        except Exception as e:
            logger.error("Failed to create synonym map: %s", e)
            return False

    # ------------------------------------------------------------------
    # Index creation (integrated vectorization)
    # ------------------------------------------------------------------

    def create_index(self) -> bool:
        """Create the search index with HNSW vectors, scalar quantization,
        an AzureOpenAI vectorizer, synonym maps, and semantic configuration.

        The vectorizer enables query-time text-to-vector conversion so callers
        can pass plain text queries without pre-computing embeddings.
        """
        if not INDEX_SDK_AVAILABLE:
            logger.error("azure-search-documents index models not available")
            return False

        if not self.search_endpoint:
            logger.error("AZURE_SEARCH_ENDPOINT not set")
            return False

        # Ensure synonym map exists before creating index
        self.create_synonym_map()

        index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self._get_credential(),
        )

        # -- Vector search: HNSW + Scalar Quantization --
        algo_cfg = _VECTOR_SEARCH_CONFIG.get("algorithm", {})
        algo_params = algo_cfg.get("parameters", {})
        compression_cfg = _VECTOR_SEARCH_CONFIG.get("compression", {})
        compression_params = compression_cfg.get("parameters", {})
        profile_cfg = _VECTOR_SEARCH_CONFIG.get("profile", {})
        vectorizer_cfg = _VECTOR_SEARCH_CONFIG.get("vectorizer", {})

        hnsw = HnswAlgorithmConfiguration(
            name=algo_cfg.get("name", "hr-hnsw-config"),
            parameters=HnswParameters(
                metric=algo_params.get("metric", "cosine"),
                m=algo_params.get("m", 4),
                ef_construction=algo_params.get("efConstruction", 400),
                ef_search=algo_params.get("efSearch", 500),
            ),
        )

        scalar_quantization = ScalarQuantizationCompression(
            compression_name=compression_cfg.get("name", "hr-scalar-quantization"),
            parameters=ScalarQuantizationParameters(
                quantized_data_type=compression_params.get("quantized_data_type", "int8"),
            ),
        )

        # -- Query-time vectorizer (AzureOpenAIVectorizer) --
        aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        if "/openai" in aoai_endpoint:
            aoai_endpoint = aoai_endpoint.split("/openai")[0]
        vectorizer_name = vectorizer_cfg.get("name", "hr-azure-openai-vectorizer")
        _embedding_cfg = _SEARCH_CONFIG.get("embedding", {})
        vectorizer_deployment = (
            _embedding_cfg.get("deployment")
            or vectorizer_cfg.get("deployment_name")
            or self.EMBEDDING_MODEL
        )
        vectorizer_model = (
            _embedding_cfg.get("model")
            or vectorizer_cfg.get("model_name")
            or self.EMBEDDING_MODEL
        )

        vectorizer = AzureOpenAIVectorizer(
            vectorizer_name=vectorizer_name,
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=aoai_endpoint,
                deployment_name=vectorizer_deployment,
                model_name=vectorizer_model,
            ),
        )

        vector_search = VectorSearch(
            algorithms=[hnsw],
            compressions=[scalar_quantization],
            vectorizers=[vectorizer],
            profiles=[
                VectorSearchProfile(
                    name=profile_cfg.get("name", "hr-vector-profile"),
                    algorithm_configuration_name=algo_cfg.get("name", "hr-hnsw-config"),
                    compression_name=compression_cfg.get("name", "hr-scalar-quantization"),
                    vectorizer_name=vectorizer_name,
                )
            ],
        )

        # -- Semantic search --
        sem_cfg_name = _SEMANTIC_SEARCH_CONFIG.get(
            "configuration_name", self._semantic_config
        )
        sem_content_fields = _SEMANTIC_SEARCH_CONFIG.get(
            "prioritized_fields", {}
        ).get("content_fields", [self._content_field])
        sem_title_field = _SEMANTIC_SEARCH_CONFIG.get(
            "prioritized_fields", {}
        ).get("title_field", None)
        sem_keywords_fields = _SEMANTIC_SEARCH_CONFIG.get(
            "prioritized_fields", {}
        ).get("keywords_fields", [])

        semantic_config = SemanticConfiguration(
            name=sem_cfg_name,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name=sem_title_field) if sem_title_field else None,
                content_fields=[SemanticField(field_name=f) for f in sem_content_fields],
                keywords_fields=[SemanticField(field_name=f) for f in sem_keywords_fields] if sem_keywords_fields else None,
            ),
        )
        semantic_search = SemanticSearch(
            default_configuration_name=sem_cfg_name,
            configurations=[semantic_config],
        )

        # -- Synonym map field names --
        synonym_fields = set(self._synonym_map_fields)

        # -- Index fields --
        def _searchable(name: str, **kwargs: Any) -> SearchField:
            """Create a SearchableField, attaching synonym map if configured."""
            if name in synonym_fields:
                kwargs["synonym_map_names"] = [self._synonym_map_name]
            return SearchableField(name=name, type=SearchFieldDataType.String, **kwargs)

        fields = [
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
                analyzer_name="keyword",
            ),
            SimpleField(name=self._blob_url_field, type="Edm.String"),
            _searchable(self._content_field),
            _searchable(self._source_field),
            _searchable(self._filename_field, filterable=True),
            _searchable(self._filepath_field, filterable=True),
            _searchable(self._parent_title_field, filterable=True),
            _searchable(self._policy_number_field, filterable=True),
            SimpleField(
                name=_SEARCH_CONFIG.get("parent_key_field", "policy_parent_id"),
                type="Edm.String",
                filterable=True,
            ),
            SearchField(
                name=self._vector_field,
                type="Collection(Edm.Single)",
                searchable=True,
                vector_search_dimensions=self.EMBEDDING_DIMENSIONS,
                vector_search_profile_name=profile_cfg.get("name", "hr-vector-profile"),
            ),
        ]

        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

        try:
            index_client.create_or_update_index(index)
            logger.info("Index '%s' created/updated (integrated vectorization)", self.index_name)
            return True
        except Exception as e:
            logger.error("Failed to create index: %s", e)
            return False

    # ------------------------------------------------------------------
    # Embedding (client-side fallback)
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector using text-embedding-3-small.

        With integrated vectorization the index's vectorizer handles
        query-time embedding, but this method is available as a fallback
        for explicit VectorizedQuery usage.
        """
        client = self._get_openai_client()
        if not client:
            return None
        try:
            response = client.embeddings.create(
                input=text, model=self.EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning("Embedding generation failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top: int | None = None,
        embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute hybrid search: full-text + vector + semantic ranker.

        Applies glossary expansion (same as legacy HRPolicySearchService)
        then uses the index's AzureOpenAI vectorizer for query-time
        embedding. Client-side embedding is used as a fallback.

        Returns:
            List of hit dicts with keys matching the original
            HRPolicySearchService format for compatibility.
        """
        expanded_query = expand_query_with_glossary(query)
        logger.info("Search query: '%s' -> expanded: '%s'", query, expanded_query)

        top = top or self._top_k
        search_client = self._get_search_client()

        search_kwargs: dict[str, Any] = {
            "search_text": expanded_query,
            "top": top,
            "include_total_count": True,
            "query_type": QueryType.SEMANTIC,
            "semantic_configuration_name": self._semantic_config,
        }

        # Vector leg — use provided embedding or generate one
        vec = embedding or self.generate_embedding(expanded_query)
        if vec:
            search_kwargs["vector_queries"] = [
                VectorizedQuery(
                    vector=vec,
                    k_nearest_neighbors=top,
                    fields=self._vector_field,
                )
            ]
            logger.info("Using hybrid search (text + vector + semantic ranker)")
        else:
            logger.info("Using text search + semantic ranker (no embedding)")

        try:
            results = search_client.search(**search_kwargs)

            hits: list[dict[str, Any]] = []
            for result in results:
                content = result.get(self._content_field, "")
                blob_url = result.get(self._blob_url_field, "")
                source = result.get(self._source_field, "") or ""
                if not source and blob_url and content:
                    source = f"{blob_url} | {content}"

                parent_title = result.get(self._parent_title_field, "")
                policy_number = self._normalize_policy_number(
                    result.get(self._policy_number_field, "")
                )

                # Map to a format compatible with HRPolicySearchService
                hits.append(
                    {
                        "id": result.get("id", ""),
                        "title": parent_title,
                        "policy_number": policy_number,
                        "category": "",
                        "content": content[:2000],
                        "score": result.get("@search.score", 0),
                        "reranker_score": result.get("@search.reranker_score"),
                        # Extended fields from integrated vectorization index
                        "source": source,
                        "filePath": result.get(self._filepath_field, ""),
                        "fileName": result.get(self._filename_field, ""),
                        "parentTitle": parent_title,
                        "blob_url": blob_url,
                    }
                )

            logger.info("Hybrid search returned %d results", len(hits))
            return hits

        except Exception as e:
            logger.error("Hybrid search failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Document count
    # ------------------------------------------------------------------

    def get_document_count(self) -> int:
        """Get the number of documents in the index."""
        try:
            search_client = self._get_search_client()
            return search_client.get_document_count()
        except Exception:
            return 0
