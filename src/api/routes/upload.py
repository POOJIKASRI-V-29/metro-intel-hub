"""
Document Ingestion API Route.

Handles HTTP multipart file uploads, parses optional metadata, and 
triggers the underlying DocumentUploadPipeline to vectorize the data.
"""

import logging
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional

# Import the Dependency Injection getter
# (Assuming dependencies.py is one level up in the api/ folder)
from ..dependencies import get_upload_pipeline

# Import the underlying pipeline and our new schema
from ...pipeline.upload_pipeline import DocumentUploadPipeline
from ..schemas.upload_schema import UploadResponse

logger = logging.getLogger("document_intelligence.api.routes.upload")

router = APIRouter(prefix="/v1/documents", tags=["Document Ingestion"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="The physical file to upload (e.g., PDF, TXT)."),
    metadata_str: Optional[str] = Form(None, alias="metadata", description="Optional JSON string containing file metadata."),
    pipeline: DocumentUploadPipeline = Depends(get_upload_pipeline)
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
            chunks_created=result.chunks_created,
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