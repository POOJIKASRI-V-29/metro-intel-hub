"""
Response schemas for the Document Intelligence Platform API.

This module defines all Pydantic models used to serialize outgoing HTTP responses.
It utilizes a generic envelope pattern (`APIResponse`) to ensure consistent data 
structures across all endpoints, simplifying client-side consumption.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

# Type variable for the generic APIResponse data payload
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response envelope for all endpoints.
    
    Attributes:
        success: Boolean indicating if the operation succeeded.
        message: Human-readable message detailing the outcome.
        data: The actual payload of the response (can be any other schema).
        errors: Optional list of error messages if the operation failed.
    """
    success: bool = Field(default=True, description="Indicates if the request was successful.")
    message: str = Field(default="Success", description="Outcome message.")
    data: Optional[T] = Field(default=None, description="The core response payload.")
    errors: Optional[List[str]] = Field(default=None, description="List of error details, if any.")


class DocumentMetadata(BaseModel):
    """
    Standardized metadata representation for a document.
    """
    document_id: str = Field(..., description="Unique identifier for the document.")
    filename: str = Field(..., description="Original name of the uploaded file.")
    department: Optional[str] = Field(default=None, description="KMRL department owning the document.")
    upload_date: datetime = Field(..., description="Timestamp of when the document was ingested.")
    file_type: str = Field(..., description="Extension or mime-type of the file (e.g., pdf, docx).")
    
    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """
    Payload for document upload and initial ingestion responses.
    """
    document_id: str = Field(..., description="The UUID assigned to the newly uploaded document.")
    filename: str = Field(..., description="The name of the file processed.")
    status: str = Field(..., description="Processing status (e.g., 'processing', 'completed').")
    chunks_created: int = Field(default=0, description="Number of vector chunks generated.")


class SearchResultItem(BaseModel):
    """
    Represents a single retrieved chunk/document in search results.
    """
    document_id: str = Field(..., description="ID of the source document.")
    chunk_id: str = Field(..., description="Unique ID of the specific text chunk.")
    text: str = Field(..., description="The actual text content of the chunk.")
    score: float = Field(..., description="Relevance score from the retrieval/reranking engine.")
    metadata: DocumentMetadata = Field(..., description="Source document metadata.")


class TextSnippetMatch(BaseModel):
    """A single matching text fragment within a document."""
    chunk_id: str = Field(..., description="Unique ID of the matching text chunk.")
    text: str = Field(..., description="The raw snippet text to display.")
    score: float = Field(..., description="Localized similarity score for this snippet.")


class SearchDocumentResult(BaseModel):
    """A grouped, document-level search result ready for UI presentation."""
    document_id: str = Field(..., description="ID of the parent document.")
    filename: str = Field(..., description="Original filename of the document.")
    aggregate_score: float = Field(..., description="Document-level relevance score (best snippet).")
    matches: List[TextSnippetMatch] = Field(
        default_factory=list, description="Relevant snippets found within this document."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document-level metadata tags."
    )


class SearchResponse(BaseModel):
    """
    Payload for document search responses.
    """
    query: str = Field(..., description="The original search query that was executed.")
    results_count: int = Field(default=0, description="Number of documents returned.")
    documents: List[SearchDocumentResult] = Field(
        default_factory=list, description="Ranked list of matching documents."
    )


class CitationSource(BaseModel):
    """A document chunk cited by the assistant in a RAG answer."""
    document_id: str = Field(..., description="ID of the cited source document.")
    filename: str = Field(..., description="Filename of the cited source.")
    page_number: Optional[Any] = Field(default=None, description="Page label/number, if known.")
    text_snippet: str = Field(..., description="The exact text used as grounding context.")
    similarity_score: Optional[float] = Field(default=None, description="Relevance score of the citation.")


class TokenUsage(BaseModel):
    """Token accounting telemetry returned by the generation engine."""
    prompt_tokens: int = Field(default=0, description="Tokens consumed by the prompt.")
    completion_tokens: int = Field(default=0, description="Tokens produced in the completion.")
    total_tokens: int = Field(default=0, description="Total tokens billed for the turn.")


class ChatResponse(BaseModel):
    """
    Payload for conversational RAG responses.
    """
    session_id: str = Field(..., description="The session ID to maintain chat history.")
    answer: str = Field(..., description="The LLM-generated response.")
    citations: List[CitationSource] = Field(
        default_factory=list,
        description="The document chunks the LLM used to ground its answer.",
    )
    usage: Optional[TokenUsage] = Field(default=None, description="Token usage telemetry, if available.")


class SummaryResponse(BaseModel):
    """
    Payload for document summarization endpoints.
    """
    document_id: str = Field(..., description="ID of the summarized document.")
    summary: str = Field(..., description="The generated summary.")
    extracted_entities: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Key entities extracted from the text, if requested."
    )


class ClassificationResponse(BaseModel):
    """
    Payload for document classification endpoints.
    """
    document_id: Optional[str] = Field(default=None, description="ID of the classified document, if applicable.")
    category: str = Field(..., description="The predicted class or category (e.g., 'Financial Report').")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the prediction (0.0 to 1.0).")
    tags: List[str] = Field(default_factory=list, description="Secondary sub-tags identified.")


class GraphQueryResponse(BaseModel):
    """
    Payload for Knowledge Graph queries.
    """
    natural_language_summary: Optional[str] = Field(
        default=None, 
        description="Plain English answer generated from the graph data."
    )
    graph_data: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Raw JSON representation of graph nodes and edges for visualization."
    )