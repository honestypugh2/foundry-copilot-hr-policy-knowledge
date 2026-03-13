"""
Azure AI Search Service Module

Handles search index creation, document indexing, and semantic search queries
for the HR policy knowledge base.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        SearchableField,
        SynonymMap,
        VectorSearch,
        VectorSearchProfile,
    )
    from azure.search.documents.models import (
        QueryType,
        VectorizedQuery,
    )
    SEARCH_SDK_AVAILABLE = True
except ImportError:
    SEARCH_SDK_AVAILABLE = False
    logger.warning("azure-search-documents not installed")

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("openai not installed, vector search unavailable")


# HR Glossary: Maps common vernacular/shorthand to formal policy terms.
# This addresses the "difficulty understanding technician vernacular" challenge.
HR_GLOSSARY = {
    "pto": "Paid Time Off",
    "time off": "Paid Time Off",
    "vacation": "Paid Time Off",
    "sick leave": "Short-Term Disability",
    "sick time": "Short-Term Disability",
    "std": "Short-Term Disability",
    "dress code": "Uniform Dress Code",
    "what to wear": "Uniform Dress Code",
    "uniforms": "Uniform Dress Code",
    "holidays": "Holiday Pay",
    "holiday pay": "Holiday Pay",
    "day off": "Holiday Pay",
    "new hire": "Probationary Period",
    "probation": "Probationary Period",
    "onboarding": "Probationary Period",
    "ethics": "Code of Ethics",
    "code of conduct": "Code of Ethics",
    "rehire": "Rehiring of Retirees",
    "re-hire": "Rehiring of Retirees",
    "retiree": "Rehiring of Retirees",
    "medical exam": "Pre-employment Medical Examinations",
    "physical": "Pre-employment Medical Examinations",
    "drug test": "Pre-employment Medical Examinations",
    "blood borne": "Blood Borne Pathogens",
    "bbp": "Blood Borne Pathogens",
    "needlestick": "Blood Borne Pathogens",
    "career path": "Career Path",
    "promotion": "Career Path",
    "advancement": "Career Path",
    "hr generalist": "HR Generalist Career Path",
    "data management": "Data Management Career Path",
    "dm": "Data Management Career Path",
    "part time pto": "Paid Time Off - Part-time",
    "part-time": "Paid Time Off - Part-time",
}


def expand_query_with_glossary(query: str) -> str:
    """
    Expand a user query with formal HR terminology from the glossary.

    This handles the "vernacular" challenge where users ask the same question
    in different ways (formal names vs shorthand/coded identifiers).
    """
    expanded = query
    query_lower = query.lower()

    for vernacular, formal_term in HR_GLOSSARY.items():
        if vernacular in query_lower and formal_term.lower() not in query_lower:
            expanded += f" {formal_term}"
            break  # Add at most one expansion to avoid over-expansion

    return expanded


class HRPolicySearchService:
    """
    Service for searching HR policy documents in Azure AI Search.

    Supports:
    - Full-text search with glossary expansion
    - Semantic search (when index is configured with semantic config)
    - Local fallback search for demo mode
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self):
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_index = os.getenv("AZURE_SEARCH_INDEX_NAME", "hr-policy-index")
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "true").lower() == "true"

        # Azure OpenAI for embeddings
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")

        self._search_client: Optional[SearchClient] = None
        self._index_client: Optional[SearchIndexClient] = None
        self._openai_client = None

    @property
    def is_configured(self) -> bool:
        """Check if Azure AI Search is configured."""
        return bool(self.search_endpoint) and SEARCH_SDK_AVAILABLE

    def _get_credential(self):
        """Get Azure credential based on configuration."""
        if self.search_key and not self.search_key.startswith("your_"):
            return AzureKeyCredential(self.search_key)
        if self.use_managed_identity:
            try:
                return AzureCliCredential()
            except Exception:
                return DefaultAzureCredential()
        raise ValueError("No valid credential for Azure AI Search")

    def get_search_client(self) -> Optional[SearchClient]:
        """Get or create SearchClient."""
        if self._search_client is None and self.is_configured:
            credential = self._get_credential()
            self._search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.search_index,
                credential=credential,
            )
        return self._search_client

    def get_index_client(self) -> Optional[SearchIndexClient]:
        """Get or create SearchIndexClient."""
        if self._index_client is None and self.is_configured:
            credential = self._get_credential()
            self._index_client = SearchIndexClient(
                endpoint=self.search_endpoint,
                credential=credential,
            )
        return self._index_client

    def get_openai_client(self):
        """Get or create Azure OpenAI client for embeddings."""
        if self._openai_client is None and OPENAI_AVAILABLE and self.openai_endpoint:
            kwargs = {
                "azure_endpoint": self.openai_endpoint,
                "api_version": self.openai_api_version,
            }
            if self.openai_key and not self.openai_key.startswith("your_"):
                kwargs["api_key"] = self.openai_key
            else:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                kwargs["azure_ad_token_provider"] = token_provider
            self._openai_client = AzureOpenAI(**kwargs)
        return self._openai_client

    def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for a text string."""
        client = self.get_openai_client()
        if not client:
            return None
        try:
            response = client.embeddings.create(
                input=text,
                model=self.EMBEDDING_MODEL,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def create_synonym_map(self) -> bool:
        """Create an Azure AI Search synonym map from the HR glossary.

        This ensures that vernacular expansion works at the index level,
        which is critical for Copilot Studio queries that bypass the
        Python backend glossary logic.
        """
        index_client = self.get_index_client()
        if not index_client:
            logger.error("Cannot create synonym map: SearchIndexClient not available")
            return False

        # Build synonym rules in Solr format: "term1,term2 => formal_term"
        rules = []
        grouped: dict[str, list[str]] = {}
        for vernacular, formal in HR_GLOSSARY.items():
            grouped.setdefault(formal, []).append(vernacular)

        for formal, vernaculars in grouped.items():
            all_terms = vernaculars + [formal]
            rules.append(",".join(all_terms))

        synonym_map = SynonymMap(
            name="hr-glossary-synonyms",
            synonyms=rules,
        )

        try:
            index_client.create_or_update_synonym_map(synonym_map)
            logger.info(f"Synonym map 'hr-glossary-synonyms' created/updated with {len(rules)} rules")
            return True
        except Exception as e:
            logger.error(f"Failed to create synonym map: {e}")
            return False

    def create_index(self) -> bool:
        """Create the HR policy search index with vector, semantic, and synonym support."""
        index_client = self.get_index_client()
        if not index_client:
            logger.error("Cannot create index: SearchIndexClient not available")
            return False

        # Ensure synonym map exists before creating index
        self.create_synonym_map()

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True, synonym_map_names=["hr-glossary-synonyms"]),
            SimpleField(name="policy_number", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="category", type=SearchFieldDataType.String, filterable=True, synonym_map_names=["hr-glossary-synonyms"]),
            SearchableField(name="content", type=SearchFieldDataType.String, synonym_map_names=["hr-glossary-synonyms"]),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.EMBEDDING_DIMENSIONS,
                vector_search_profile_name="hr-vector-profile",
            ),
            SimpleField(name="file_path", type=SearchFieldDataType.String),
            SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="word_count", type=SearchFieldDataType.Int32),
            SimpleField(name="indexed_date", type=SearchFieldDataType.String, sortable=True),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hr-hnsw-config")],
            profiles=[VectorSearchProfile(name="hr-vector-profile", algorithm_configuration_name="hr-hnsw-config")],
        )

        semantic_config = SemanticConfiguration(
            name="hr-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")],
                keywords_fields=[SemanticField(field_name="category")],
            ),
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])

        index = SearchIndex(
            name=self.search_index,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

        try:
            index_client.create_or_update_index(index)
            logger.info(f"Search index '{self.search_index}' created/updated with vector + semantic support")
            return True
        except Exception as e:
            logger.error(f"Failed to create search index: {e}")
            return False

    def upload_documents(self, documents: list[dict[str, Any]]) -> int:
        """Upload documents to the search index."""
        search_client = self.get_search_client()
        if not search_client:
            logger.error("Cannot upload: SearchClient not available")
            return 0

        try:
            result = search_client.upload_documents(documents)
            succeeded = sum(1 for r in result if r.succeeded)
            logger.info(f"Uploaded {succeeded}/{len(documents)} documents to search index")
            return succeeded
        except Exception as e:
            logger.error(f"Failed to upload documents: {e}")
            return 0

    def search(self, query: str, top: int = 5) -> list[dict[str, Any]]:
        """
        Hybrid search: full-text + vector + semantic ranker.

        Applies glossary expansion to handle vernacular queries,
        generates an embedding for vector similarity, and uses
        the semantic ranker for reranking.
        """
        expanded_query = expand_query_with_glossary(query)
        logger.info(f"Search query: '{query}' -> expanded: '{expanded_query}'")

        search_client = self.get_search_client()
        if not search_client:
            logger.warning("Azure AI Search not available, returning empty results")
            return []

        try:
            search_kwargs: dict[str, Any] = {
                "search_text": expanded_query,
                "top": top,
                "include_total_count": True,
                "query_type": QueryType.SEMANTIC,
                "semantic_configuration_name": "hr-semantic-config",
            }

            # Add vector query when embeddings are available
            embedding = self.generate_embedding(expanded_query)
            if embedding:
                vector_query = VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=top,
                    fields="content_vector",
                )
                search_kwargs["vector_queries"] = [vector_query]
                logger.info("Using hybrid search (text + vector + semantic ranker)")
            else:
                logger.info("Using text search + semantic ranker (no embedding available)")

            results = search_client.search(**search_kwargs)

            documents = []
            for result in results:
                doc = {
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "policy_number": result.get("policy_number", ""),
                    "category": result.get("category", ""),
                    "content": result.get("content", "")[:2000],
                    "score": result.get("@search.score", 0),
                    "reranker_score": result.get("@search.reranker_score"),
                }
                documents.append(doc)

            logger.info(f"Search returned {len(documents)} results")
            return documents

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_document_count(self) -> int:
        """Get the number of documents in the index."""
        search_client = self.get_search_client()
        if not search_client:
            return 0
        try:
            return search_client.get_document_count()
        except Exception:
            return 0
