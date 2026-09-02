"""
Schemas for document ingestion API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class UploadResponse(BaseModel):
    """
    Standardized response returned after successfully processing and vectorizing a document.
    """
    filename: str = Field(..., description="The original name of the uploaded file.")
    document_id: str = Field(..., description="The unique system-generated ID for this document.")
    status: str = Field(..., description="The result status of the ingestion pipeline (e.g., 'success').")
    chunks_created: int = Field(default=0, description="Total number of semantic vector chunks generated.")
    metadata_attached: Optional[Dict[str, Any]] = Field(default=None, description="The metadata stored with the document.")

class DocumentSummary(BaseModel):
    """
    A single indexed document, folded up from the chunks stored for it.
    """
    document_id: str = Field(..., description="Unique system-generated ID for the document.")
    filename: str = Field(..., description="Original name of the uploaded file.")
    extension: Optional[str] = Field(default=None, description="File extension, including the leading dot.")
    chunk_count: int = Field(default=0, description="Number of indexed chunks belonging to this document.")
    upload_date: Optional[str] = Field(default=None, description="ISO-8601 UTC timestamp of ingestion, when recorded.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata supplied at upload time.")


class DocumentListResponse(BaseModel):
    """
    The set of documents currently retrievable from the vector store.
    """
    total: int = Field(default=0, description="Number of distinct documents returned.")
    documents: List[DocumentSummary] = Field(default_factory=list, description="Indexed documents, ordered by filename.")
    truncated: bool = Field(
        default=False,
        description=(
            "True when the scan bound was reached with chunks still unread, so `total` "
            "is a floor rather than the size of the corpus."
        ),
    )
