"""FastAPI router for document metadata operations in the KMRL platform.

Scope: Provides endpoints to extract, retrieve, and update metadata attributes 
(e.g., author, creation date, keywords, document type) for ingested documents.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from utils.constants import ErrorCode

logger = get_logger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


class MetadataResponse(BaseModel):
    """Schema representing the metadata associated with a document."""
    document_id: str
    title: str | None = Field(default=None, description="Extracted or original document title.")
    author: str | None = Field(default=None, description="Primary author or organizational unit.")
    creation_date: str | None = Field(default=None, description="ISO 8601 formatted date string.")
    keywords: List[str] = Field(default_factory=list, description="Extracted key topics or terms.")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata.")


@router.get(
    "/{document_id}",
    response_model=MetadataResponse,
    summary="Retrieve metadata for a specific document"
)
async def get_document_metadata(
    document_id: str = Path(..., description="The unique identifier of the document")
) -> MetadataResponse:
    """Fetches the stored metadata attributes for a given document.
    
    This is typically used by the frontend to display document details 
    before a user decides to open or download the full text.
    """
    logger.info(f"Retrieving metadata for document: {document_id}")

    try:
        # TODO: Replace with actual database retrieval logic (e.g., PostgreSQL or MongoDB)
        # Simulated successful response
        return MetadataResponse(
            document_id=document_id,
            title="KMRL Q3 Maintenance Report",
            author="Engineering Division",
            creation_date="2026-07-01",
            keywords=["maintenance", "Q3", "track inspection", "safety"]
        )
    except Exception as exc:
        logger.error(f"Failed to retrieve metadata for {document_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.RESOURCE_NOT_FOUND,
                "message": f"Metadata for document {document_id} could not be found."
            }
        )


@router.post(
    "/{document_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger async metadata extraction for a document"
)
async def extract_metadata(
    document_id: str = Path(..., description="The unique identifier of the document")
) -> Dict[str, str]:
    """Triggers the metadata extraction agent to process a document.
    
    This is an asynchronous operation. The endpoint returns a 202 Accepted status 
    indicating that the job has been queued.
    """
    logger.info(f"Queueing metadata extraction job for document: {document_id}")

    # TODO: Dispatch job to Celery / BackgroundTasks pointing to `agents/metadata_agent.py`
    
    return {
        "status": "accepted",
        "document_id": document_id,
        "message": "Metadata extraction job has been queued."
    }