"""
Schemas for document ingestion API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class UploadResponse(BaseModel):
    """
    Standardized response returned after successfully processing and vectorizing a document.
    """
    filename: str = Field(..., description="The original name of the uploaded file.")
    document_id: str = Field(..., description="The unique system-generated ID for this document.")
    status: str = Field(..., description="The result status of the ingestion pipeline (e.g., 'success').")
    chunks_created: int = Field(default=0, description="Total number of semantic vector chunks generated.")
    metadata_attached: Optional[Dict[str, Any]] = Field(default=None, description="The metadata stored with the document.")