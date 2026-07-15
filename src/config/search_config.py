"""
Shared Search Configuration Module

Loads search_config.json and exposes typed accessors for all sections.
Both Pattern 1 (Copilot Studio → AI Search Knowledge Source) and
Pattern 2 (Foundry Agent Action) consume the same configuration
to ensure consistent index schema, synonym maps, semantic ranking,
and category metadata across all workflows.

Usage:
    from src.config.search_config import search_cfg

    index_name = search_cfg.index_name
    synonym_map_name = search_cfg.synonym_map_name
    vectorizer_deployment = search_cfg.vectorizer_deployment
    agentic_retrieval = search_cfg.agentic_retrieval
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent / "search_config.json"


def _load_config() -> dict[str, Any]:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    logger.warning("search_config.json not found at %s", _CONFIG_PATH)
    return {}


@dataclass(frozen=True)
class SearchConfig:
    """Typed wrapper around search_config.json."""

    _raw: dict[str, Any] = field(repr=False)

    # -- search_config section --
    @property
    def index_name(self) -> str:
        return self._raw.get("search_config", {}).get("index_name", "hr-policy-index")

    @property
    def semantic_configuration(self) -> str:
        return self._raw.get("search_config", {}).get("semantic_configuration", "hr-semantic-config")

    @property
    def vector_field(self) -> str:
        return self._raw.get("search_config", {}).get("vector_field", "policy_vector")

    @property
    def content_field(self) -> str:
        return self._raw.get("search_config", {}).get("content_field", "policy")

    @property
    def source_field(self) -> str:
        return self._raw.get("search_config", {}).get("source_field", "policy_with_source")

    @property
    def blob_url_field(self) -> str:
        return self._raw.get("search_config", {}).get("blob_url_field", "blob_url")

    @property
    def parent_key_field(self) -> str:
        return self._raw.get("search_config", {}).get("parent_key_field", "policy_parent_id")

    @property
    def filename_field(self) -> str:
        return self._raw.get("search_config", {}).get("filename_field", "metadata_storage_name")

    @property
    def filepath_field(self) -> str:
        return self._raw.get("search_config", {}).get("filepath_field", "metadata_storage_path")

    @property
    def parent_title_field(self) -> str:
        return self._raw.get("search_config", {}).get("parent_title_field", "parent_title")

    @property
    def policy_number_field(self) -> str:
        return self._raw.get("search_config", {}).get("policy_number_field", "policy_number")

    @property
    def top_k(self) -> int:
        return self._raw.get("search_config", {}).get("top_k", 5)

    # -- synonym_map section --
    @property
    def synonym_map_name(self) -> str:
        return self._raw.get("synonym_map", {}).get("name", "hr-glossary-synonyms")

    @property
    def synonym_map_fields(self) -> list[str]:
        return self._raw.get("synonym_map", {}).get("fields", ["parent_title", "policy", "policy_with_source"])

    # -- vector_search section --
    @property
    def vector_search(self) -> dict[str, Any]:
        return self._raw.get("vector_search", {})

    # -- embedding section (single source of truth for the embedding model) --
    @property
    def embedding(self) -> dict[str, Any]:
        return self._raw.get("embedding", {})

    @property
    def embedding_deployment(self) -> str:
        return (
            self.embedding.get("deployment")
            or self.vector_search.get("vectorizer", {}).get("deployment_name")
            or "text-embedding-3-small"
        )

    @property
    def embedding_model(self) -> str:
        return (
            self.embedding.get("model")
            or self.vector_search.get("vectorizer", {}).get("model_name")
            or "text-embedding-3-small"
        )

    @property
    def embedding_dimensions(self) -> int:
        return (
            self.embedding.get("dimensions")
            or self.vector_search.get("vectorizer", {}).get("dimensions")
            or 1536
        )

    # Backward-compatible aliases (delegate to the embedding block).
    @property
    def vectorizer_deployment(self) -> str:
        return self.embedding_deployment

    @property
    def vectorizer_model(self) -> str:
        return self.embedding_model

    # -- semantic_search section --
    @property
    def semantic_search(self) -> dict[str, Any]:
        return self._raw.get("semantic_search", {})

    # -- skillset section (SplitSkill pipeline) --
    @property
    def skillset(self) -> dict[str, Any]:
        return self._raw.get("skillset", {})

    # -- document_layout_skillset section (Document Intelligence Layout pipeline) --
    @property
    def document_layout_skillset(self) -> dict[str, Any]:
        return self._raw.get("document_layout_skillset", {})

    # -- blob_storage section --
    @property
    def blob_container_name(self) -> str:
        return self._raw.get("blob_storage", {}).get("container_name", "ask-hr-knowledge")

    @property
    def included_extensions(self) -> list[str]:
        return self._raw.get("blob_storage", {}).get(
            "included_extensions",
            [".docx", ".doc", ".pdf", ".xlsx", ".pptx", ".html"],
        )

    # -- indexer section --
    @property
    def indexer(self) -> dict[str, Any]:
        return self._raw.get("indexer", {})

    @property
    def indexer_data_source_name(self) -> str:
        return self.indexer.get("data_source_name") or f"{self.index_name}-blob-ds"

    @property
    def indexer_name(self) -> str:
        return self.indexer.get("name") or f"{self.index_name}-indexer"

    @property
    def indexer_api_version(self) -> str:
        return self.indexer.get("api_version", "2024-07-01")

    @property
    def indexer_batch_size(self) -> int:
        return self.indexer.get("batch_size", 1)

    @property
    def indexer_data_to_extract(self) -> str:
        return self.indexer.get("data_to_extract", "contentAndMetadata")

    @property
    def indexer_parsing_mode(self) -> str:
        return self.indexer.get("parsing_mode", "default")

    @property
    def indexer_allow_skillset_to_read_file_data(self) -> bool:
        return self.indexer.get("allow_skillset_to_read_file_data", True)

    @property
    def indexer_field_mappings(self) -> list[dict[str, str]]:
        return self.indexer.get(
            "field_mappings",
            [
                {"source": "metadata_storage_path", "target": "metadata_storage_path"},
                {"source": "metadata_storage_name", "target": "metadata_storage_name"},
            ],
        )

    # -- agentic_retrieval section (Pattern 2) --
    @property
    def agentic_retrieval(self) -> dict[str, Any]:
        return self._raw.get("agentic_retrieval", {})

    @property
    def knowledge_base_name(self) -> str:
        return self.agentic_retrieval.get("knowledge_base_name", "hr-knowledge-base")

    @property
    def knowledge_source_name(self) -> str:
        return self.agentic_retrieval.get("knowledge_source_name", "hr-knowledge-source")

    @property
    def mcp_connection_name(self) -> str:
        return self.agentic_retrieval.get("mcp", {}).get("project_connection_name", "hr-knowledge-mcp-connection")

    # -- foundry_agent section --
    @property
    def foundry_agent(self) -> dict[str, Any]:
        return self._raw.get("foundry_agent", {})

    # -- Raw access --
    @property
    def raw(self) -> dict[str, Any]:
        return self._raw


# Module-level singleton
search_cfg = SearchConfig(_raw=_load_config())
