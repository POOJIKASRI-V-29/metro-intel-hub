"""
Document Ingestion API Routes.

Handles HTTP multipart file uploads, parses optional metadata, and triggers the
underlying DocumentUploadPipeline to vectorize the data. Also serves the listing of
what is currently indexed, which listing UIs need to show a corpus at all.
"""

import logging
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional, TYPE_CHECKING

# Import the Dependency Injection getter
# (Assuming dependencies.py is one level up in the api/ folder)
from ..dependencies import get_upload_pipeline, get_vector_store

# The concrete pipeline pulls the heavy ML stack (torch / qdrant); import it only for
# type-checking so this route module stays importable without those dependencies.
from ..schemas.upload_schema import DocumentListResponse, DocumentSummary, UploadResponse

if TYPE_CHECKING:
    from ...pipeline.upload_pipeline import DocumentUploadPipeline

logger = logging.getLogger("document_intelligence.api.routes.upload")

router = APIRouter(prefix="/v1/documents", tags=["Document Ingestion"])

# Must match DocumentUploadPipeline / RetrievalPipeline's target_collection.
TARGET_COLLECTION = "kmrl_enterprise_docs"


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="The physical file to upload (e.g., PDF, TXT)."),
    metadata_str: Optional[str] = Form(None, alias="metadata", description="Optional JSON string containing file metadata."),
    pipeline: "DocumentUploadPipeline" = Depends(get_upload_pipeline)
):
    """
    Receives a file upload, processes it through the ingestion pipeline, 
    and stores the resulting vectors in the database.
    """
    logger.info(f"API Request: /upload | Filename: '{file.filename}'")
    
    # 1. Parse optional metadata from the form data
    user_metadata = {}
    if metadata_str:
        try:
            user_metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse metadata JSON string.")
            raise HTTPException(status_code=400, detail="Invalid JSON format in 'metadata' field.")

    # 2. Extract file details
    filename = file.filename or "unknown_file"
    file_size = file.size or 0

    try:
        # 3. Stream the file directly into the pipeline
        # We use file.file (which is a SpooledTemporaryFile) so we don't load huge PDFs entirely into RAM
        result = pipeline.process_document(
            file_stream=file.file,
            filename=filename,
            file_size=file_size,
            user_metadata=user_metadata
        )

        # 4. Map the internal pipeline result to our external API schema
        return UploadResponse(
            filename=filename,
            document_id=result.document_id,
            status=result.status,
            chunks_created=result.chunks_processed,
            metadata_attached=user_metadata
        )

    except ValueError as ve:
        logger.warning(f"Validation error during file processing: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Internal server error during document upload.")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing the document.")
    finally:
        # Always ensure the file stream is closed to prevent memory/file-descriptor leaks
        file.file.close()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    store = Depends(get_vector_store),
) -> DocumentListResponse:
    """
    Lists every document currently indexed in the vector store.

    There is no separate document database: this is folded up from the chunk payloads,
    so a document appears here exactly when it is retrievable by search and chat.
    """
    logger.info("API Request: GET /v1/documents")

    if not hasattr(store, "list_documents"):
        raise HTTPException(
            status_code=501,
            detail="The configured vector store cannot enumerate documents.",
        )

    try:
        result = store.list_documents(collection_name=TARGET_COLLECTION)
    except Exception as error:
        logger.exception("Failed to list indexed documents.")
        raise HTTPException(
            status_code=503,
            detail="The vector store is unavailable, so indexed documents cannot be listed.",
        ) from error

    documents = [DocumentSummary(**record) for record in result["documents"]]
    if result["truncated"]:
        logger.warning(
            "Document listing truncated after scanning %d chunks; returning %d documents.",
            result["scanned_chunks"],
            len(documents),
        )

    return DocumentListResponse(
        total=len(documents),
        documents=documents,
        truncated=result["truncated"],
    )
