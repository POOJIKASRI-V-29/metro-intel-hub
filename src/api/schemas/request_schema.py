"""
Request schemas for the Document Intelligence Platform API.

This module contains all Pydantic models used to validate incoming HTTP requests.
It strictly enforces types, boundaries, and required fields before data reaches 
the business or AI logic layers.
"""

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SearchType(str, Enum):
    """Enumeration of supported search methodologies."""
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"
    GRAPH = "graph"


class SummaryLength(str, Enum):
    """Enumeration of supported summary lengths."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class SearchRequest(BaseModel):
    """
    Schema for document search requests.
    
    Attributes:
        query: The natural language search query.
        search_type: The retrieval methodology to use.
        top_k: Number of documents to retrieve.
        filters: Optional dictionary for metadata filtering (e.g., department, date).
        use_reranker: Flag to enable cross-encoder reranking for precision.
    """
    query: str = Field(..., min_length=1, description="The natural language query string.")
    search_type: SearchType = Field(
        default=SearchType.HYBRID, 
        description="Search methodology to utilize."
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of results to return.")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Key-value pairs for metadata filtering (e.g., {'department': 'HR'})."
    )
    use_reranker: bool = Field(
        default=True, 
        description="If true, applies a cross-encoder model to re-rank initial hits."
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, value: str) -> str:
        """
        Validates that the query is not just whitespace.
        
        Args:
            value: The query string.
            
        Returns:
            The stripped query string.
            
        Raises:
            ValueError: If the query contains only whitespace.
        """
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Query string cannot be empty or only whitespace.")
        return stripped_value


class ChatMessage(BaseModel):
    """
    Schema representing a single message in a chat history.
    
    Attributes:
        role: The author of the message (user, assistant, or system).
        content: The text content of the message.
    """
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Role of the messenger.")
    content: str = Field(..., min_length=1, description="Text content of the message.")


class ChatRequest(BaseModel):
    """
    Schema for RAG-powered chat requests.
    
    Attributes:
        session_id: Unique identifier for the conversation thread.
        message: The new message from the user.
        chat_history: Previous messages in the conversation to maintain context.
        document_ids: Optional list of document IDs to restrict the RAG context.
    """
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique UUID for tracking chat sessions."
    )
    message: str = Field(..., min_length=1, description="The user's query or statement.")
    chat_history: List[ChatMessage] = Field(
        default_factory=list, 
        description="Contextual history of the current chat session."
    )
    document_ids: Optional[List[str]] = Field(
        default=None, 
        description="If provided, scopes the RAG context exclusively to these documents."
    )


class SummarizeRequest(BaseModel):
    """
    Schema for document summarization requests.
    
    Attributes:
        document_id: The unique ID of the document to summarize.
        length: Desired length of the summary.
        extract_entities: Whether to also extract and return key entities.
    """
    document_id: str = Field(..., min_length=1, description="Unique identifier of the document.")
    length: SummaryLength = Field(default=SummaryLength.MEDIUM, description="Desired summary verbosity.")
    extract_entities: bool = Field(
        default=False, 
        description="If true, triggers the knowledge graph agent to extract key entities."
    )


class ClassifyRequest(BaseModel):
    """
    Schema for document classification requests.
    
    Attributes:
        document_id: ID of an existing document to classify.
        text: Raw text to classify directly without storing a document.
    """
    document_id: Optional[str] = Field(default=None, description="ID of the stored document.")
    text: Optional[str] = Field(default=None, description="Raw text to classify on the fly.")

    @field_validator("text")
    @classmethod
    def validate_classification_target(cls, text: Optional[str], info: Any) -> Optional[str]:
        """
        Ensures that exactly one classification target (document_id or text) is provided.
        
        Args:
            text: The raw text string.
            info: Pydantic validation info containing other fields.
            
        Returns:
            The validated text string.
            
        Raises:
            ValueError: If neither or both document_id and text are provided.
        """
        document_id = info.data.get("document_id")
        if not document_id and not text:
            raise ValueError("Must provide either 'document_id' or 'text' for classification.")
        if document_id and text:
            raise ValueError("Cannot provide both 'document_id' and 'text'. Choose one.")
        return text


class GraphQueryRequest(BaseModel):
    """
    Schema for direct Knowledge Graph queries.
    
    Attributes:
        natural_language_query: User's question in plain English.
        cypher_query: Direct Cypher query string (usually for admin/debug).
    """
    natural_language_query: Optional[str] = Field(
        default=None, 
        description="Plain English query to be converted to Cypher by the LLM."
    )
    cypher_query: Optional[str] = Field(
        default=None, 
        description="Raw Cypher query to execute directly against Neo4j."
    )

    @field_validator("cypher_query")
    @classmethod
    def validate_graph_query(cls, cypher_query: Optional[str], info: Any) -> Optional[str]:
        """
        Ensures at least one querying method is provided for the Knowledge Graph.
        
        Args:
            cypher_query: The raw cypher query string.
            info: Pydantic validation info.
            
        Returns:
            The validated cypher query.
            
        Raises:
            ValueError: If neither querying mechanism is provided.
        """
        nl_query = info.data.get("natural_language_query")
        if not nl_query and not cypher_query:
            raise ValueError("Must provide either 'natural_language_query' or 'cypher_query'.")
        return cypher_query