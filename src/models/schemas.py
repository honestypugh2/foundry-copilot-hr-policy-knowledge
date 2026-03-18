"""
Pydantic models for the HR Policy Knowledge Agent.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PolicyCategory(str, Enum):
    """Categories of HR policies."""
    HIRING = "hiring"
    LEAVE = "leave"
    CAREER_PATH = "career_path"
    COMPENSATION = "compensation"
    OPERATIONAL = "operational"
    ETHICS = "ethics"
    SAFETY = "safety"
    GENERAL = "general"


class DocumentMetadata(BaseModel):
    """Metadata for a processed HR policy document."""
    id: str
    title: str
    policy_number: str = ""
    category: PolicyCategory = PolicyCategory.GENERAL
    content: str = ""
    content_preview: str = ""
    page_count: int = 0
    word_count: int = 0
    file_path: str = ""
    file_type: str = ""
    last_modified: str = ""
    indexed_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "knowledge_base"


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatRequest(BaseModel):
    """Request to chat with the HR policy agent."""
    message: str
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    use_azure: bool = True


class ChatResponse(BaseModel):
    """Response from the HR policy agent."""
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    policy_references: list[str] = Field(default_factory=list)
    glossary_matches: list[dict[str, str]] = Field(default_factory=list)
    processing_time_ms: int = 0


class AzureServiceStatus(BaseModel):
    """Status of Azure service configuration."""
    azure_openai: bool = False
    document_intelligence: bool = False
    ai_search: bool = False
    ai_foundry: bool = False


class ServiceStatus(BaseModel):
    """Status of a single Azure service."""
    name: str
    status: str  # "healthy", "available", "configured", "unavailable"
    details: str = ""


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    version: str
    services: dict[str, ServiceStatus] = Field(default_factory=dict)


class KnowledgeBaseInfo(BaseModel):
    """Information about the knowledge base."""
    total_documents: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    documents: list[dict[str, str]] = Field(default_factory=list)
    index_status: str = "unknown"


class GlossaryEntry(BaseModel):
    """A glossary entry mapping vernacular to formal terms."""
    term: str
    aliases: list[str] = Field(default_factory=list)
    definition: str = ""
    related_policies: list[str] = Field(default_factory=list)
