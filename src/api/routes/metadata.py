"""FastAPI router for document metadata operations in the KMRL platform.

Scope: Provides endpoints to extract, retrieve, and update metadata attributes 
(e.g., author, creation date, keywords, document type) for ingested documents.

A document is not a first-class record: it is the set of vector-store chunks sharing a
``document_id``. Metadata is therefore read from, and written back to, chunk payloads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from config.logging import get_logger
from src.api.dependencies import get_metadata_agent, get_vector_store
from src.utils.constants import ErrorCode

if TYPE_CHECKING:
    from src.agents.metadata_agent import MetadataAgent
    from src.vector_store.qdrant_provider import QdrantProvider

logger = get_logger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])

# Collection the upload pipeline writes document chunks into.
DOCUMENTS_COLLECTION = "kmrl_enterprise_docs"

# Extraction reads only the opening of a document, where title/author/date live.
EXTRACTION_MAX_CHUNKS = 6
EXTRACTION_MAX_CHARS = 8000

# Payload keys with a dedicated field on MetadataResponse, or internal to chunk storage.
_MAPPED_KEYS = {"title", "author", "creation_date", "keywords"}
_INTERNAL_KEYS = {"chunk_id", "chunk_index", "document_id", "text"}

# Placeholder the extraction agent emits for values it could not find.
_UNKNOWN = "unknown"


class MetadataResponse(BaseModel):
    """Schema representing the metadata associated with a document."""
    document_id: str
    title: str | None = Field(default=None, description="Extracted or original document title.")
    author: str | None = Field(default=None, description="Primary author or organizational unit.")
    creation_date: str | None = Field(default=None, description="ISO 8601 formatted date string.")
    keywords: List[str] = Field(default_factory=list, description="Extracted key topics or terms.")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata.")


def _store_unavailable(exc: Exception) -> HTTPException:
    logger.error(f"Vector store request failed: {exc}")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error_code": ErrorCode.VECTOR_STORE_UNAVAILABLE.value,
            "message": "The document store is currently unavailable."
        }
    )


def _document_not_found(document_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error_code": ErrorCode.DOCUMENT_NOT_FOUND.value,
            "message": f"Document {document_id} could not be found."
        }
    )


def _payload_to_metadata(document_id: str, payload: Dict[str, Any]) -> MetadataResponse:
    """Maps one chunk payload onto the API's MetadataResponse."""
    keywords = payload.get("keywords")
    if not isinstance(keywords, list):
        keywords = [str(keywords)] if keywords else []

    custom = {
        key: value
        for key, value in payload.items()
        if key not in _MAPPED_KEYS and key not in _INTERNAL_KEYS
    }

    return MetadataResponse(
        document_id=document_id,
        title=payload.get("title") or payload.get("filename"),
        author=payload.get("author"),
        creation_date=payload.get("creation_date"),
        keywords=[str(k) for k in keywords],
        # Carries filename, extension, upload_date and anything supplied at upload time.
        custom_attributes=custom,
    )


def _usable(value: Any) -> bool:
    """True for a non-empty value that is not the agent's 'Unknown' placeholder."""
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() != _UNKNOWN


def _run_extraction(
    document_id: str,
    agent: "MetadataAgent",
    store: "QdrantProvider",
) -> None:
    """Background job: extract metadata from a document's opening chunks and persist it.

    Runs after the 202 response has been sent, so failures are logged, not raised.
    """
    try:
        payloads = store.get_document_chunks(
            DOCUMENTS_COLLECTION, document_id, max_chunks=EXTRACTION_MAX_CHUNKS, with_text=True
        )
        text = "\n\n".join(p.get("text", "") for p in payloads if p.get("text"))[:EXTRACTION_MAX_CHARS]
        if not text.strip():
            logger.warning(f"No text available to extract metadata from for document {document_id}.")
            return

        result = agent.extract_metadata(text, strict=True)

        # Never persist the agent's "Unknown" placeholders: they would overwrite real
        # values and read as genuine metadata downstream.
        update: Dict[str, Any] = {
            key: value
            for key, value in (
                ("title", result.title),
                ("author", result.author),
                ("creation_date", result.creation_date),
                ("document_type", result.document_type),
            )
            if _usable(value)
        }
        keywords = [k for k in result.keywords if _usable(k)]
        if keywords:
            update["keywords"] = keywords

        if not update:
            logger.warning(f"Metadata extraction found nothing usable for document {document_id}.")
            return

        store.update_document_payload(DOCUMENTS_COLLECTION, document_id, update)
        logger.info(f"Persisted extracted metadata for document {document_id}: {sorted(update)}")
    except Exception as exc:  # noqa: BLE001 - background task; nothing left to raise to
        logger.exception(f"Metadata extraction failed for document {document_id}: {exc}")


@router.get(
    "/{document_id}",
    response_model=MetadataResponse,
    summary="Retrieve metadata for a specific document"
)
async def get_document_metadata(
    document_id: str = Path(..., description="The unique identifier of the document"),
    store: "QdrantProvider" = Depends(get_vector_store),
) -> MetadataResponse:
    """Fetches the stored metadata attributes for a given document.
    
    This is typically used by the frontend to display document details 
    before a user decides to open or download the full text.
    """
    logger.info(f"Retrieving metadata for document: {document_id}")

    try:
        chunks = await run_in_threadpool(
            store.get_document_chunks, DOCUMENTS_COLLECTION, document_id, 1, False
        )
    except RuntimeError as exc:
        raise _store_unavailable(exc) from exc

    if not chunks:
        raise _document_not_found(document_id)

    return _payload_to_metadata(document_id, chunks[0])


@router.post(
    "/{document_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger async metadata extraction for a document"
)
async def extract_metadata(
    background_tasks: BackgroundTasks,
    document_id: str = Path(..., description="The unique identifier of the document"),
    agent: "MetadataAgent" = Depends(get_metadata_agent),
    store: "QdrantProvider" = Depends(get_vector_store),
) -> Dict[str, str]:
    """Triggers the metadata extraction agent to process a document.
    
    This is an asynchronous operation. The endpoint returns a 202 Accepted status 
    indicating that the job has been queued.
    """
    logger.info(f"Queueing metadata extraction job for document: {document_id}")

    try:
        chunks = await run_in_threadpool(
            store.get_document_chunks, DOCUMENTS_COLLECTION, document_id, 1, False
        )
    except RuntimeError as exc:
        raise _store_unavailable(exc) from exc

    if not chunks:
        raise _document_not_found(document_id)

    background_tasks.add_task(_run_extraction, document_id, agent, store)

    return {
        "status": "accepted",
        "document_id": document_id,
        "message": "Metadata extraction job has been queued."
    }
