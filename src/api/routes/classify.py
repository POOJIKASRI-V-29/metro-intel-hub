"""FastAPI router for document and text classification.

Scope: Provides endpoints to categorize raw text snippets or ingested documents 
into the fixed taxonomy defined by `DocumentCategory`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from config.logging import get_logger
from src.utils.constants import ErrorCode, DocumentCategory

logger = get_logger(__name__)

router = APIRouter(prefix="/classify", tags=["Classification"])


class ClassificationRequest(BaseModel):
    """Schema for submitting raw text for classification."""
    text: str = Field(..., min_length=10, description="The text content to classify.")
    context_id: str | None = Field(default=None, description="Optional ID for tracking.")


class ClassificationResponse(BaseModel):
    """Schema for the classification result."""
    category: DocumentCategory
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str | None = None


@router.post(
    "/text",
    response_model=ClassificationResponse,
    summary="Classify a raw text snippet"
)
async def classify_text(payload: ClassificationRequest) -> ClassificationResponse:
    """Analyzes a text payload and assigns it to a canonical DocumentCategory.

    Typically, this delegates the heavy lifting to `agents/classifier_agent.py` 
    to prompt an LLM or use a zero-shot classification model.
    """
    logger.info(f"Received classification request for text snippet (Length: {len(payload.text)})")

    try:
        # TODO: Inject and call `agents/classifier_agent.py` here
        # Example of a simulated successful response:
        simulated_category = DocumentCategory.SAFETY_CIRCULAR
        
        return ClassificationResponse(
            category=simulated_category,
            confidence_score=0.92,
            reasoning="The text extensively references PPE and hazard protocols."
        )
        
    except Exception as exc:
        logger.error(f"Classification pipeline failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.LLM_REQUEST_FAILED, 
                "message": "The classification agent failed to process the request."
            }
        )