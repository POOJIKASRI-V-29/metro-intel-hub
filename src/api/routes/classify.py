"""FastAPI router for document and text classification.

Scope: Provides endpoints to categorize raw text snippets or ingested documents 
into the fixed taxonomy defined by `DocumentCategory`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from config.logging import get_logger
from src.api.dependencies import get_classifier_agent
from src.utils.constants import ErrorCode, DocumentCategory

if TYPE_CHECKING:
    from src.agents.classifier_agent import ClassifierAgent

logger = get_logger(__name__)

router = APIRouter(prefix="/classify", tags=["Classification"])


class ClassificationRequest(BaseModel):
    """Schema for submitting raw text for classification."""
    text: str = Field(..., min_length=10, description="The text content to classify.")
    context_id: str | None = Field(default=None, description="Optional ID for tracking.")

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


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
async def classify_text(
    payload: ClassificationRequest,
    agent: "ClassifierAgent" = Depends(get_classifier_agent),
) -> ClassificationResponse:
    """Analyzes a text payload and assigns it to a canonical DocumentCategory.

    Delegates to `agents/classifier_agent.py`. A category the model invents that is
    outside the taxonomy is reported as `DocumentCategory.OTHER`.
    """
    logger.info(
        f"Received classification request for text snippet "
        f"(Length: {len(payload.text)}, Context: {payload.context_id})"
    )

    try:
        # The agent makes a blocking LLM call; keep it off the event loop.
        result = await run_in_threadpool(agent.classify_text, payload.text)
    except ValueError as exc:
        # The agent folds LLM transport and response-parse failures into ValueError.
        logger.error(f"Classification agent failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": ErrorCode.LLM_REQUEST_FAILED.value,
                "message": "The classification agent failed to process the request."
            }
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected classification failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred while classifying the text."
            }
        ) from exc

    return ClassificationResponse(
        category=result.category,
        confidence_score=result.confidence,
        reasoning=result.reasoning,
    )
