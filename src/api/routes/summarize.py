"""FastAPI router for text and document summarization.

Scope: Exposes endpoints to condense large texts or retrieved documents 
into concise summaries using the platform's LLM integration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from utils.constants import ErrorCode

logger = get_logger(__name__)

router = APIRouter(prefix="/summarize", tags=["Summarization"])


class SummarizeTextRequest(BaseModel):
    """Schema for submitting raw text to be summarized."""
    text: str = Field(..., min_length=50, description="The full text content to summarize.")
    max_length_words: int = Field(default=150, ge=10, le=500, description="Target maximum word count for the summary.")
    focus_area: str | None = Field(default=None, description="Optional specific topic to focus the summary on.")


class SummarizeResponse(BaseModel):
    """Schema for the summarization output."""
    summary: str
    original_length_chars: int
    summary_length_chars: int


@router.post(
    "/text",
    response_model=SummarizeResponse,
    summary="Generate a summary for a provided text snippet"
)
async def summarize_text(payload: SummarizeTextRequest) -> SummarizeResponse:
    """Processes a raw text payload and returns a condensed summary.
    
    Can optionally accept a `focus_area` to tailor the summary (e.g., 
    'Summarize this text with a focus on safety protocols').
    """
    logger.info(f"Received summarization request (Text length: {len(payload.text)}, Focus: {payload.focus_area})")

    try:
        # TODO: Pass this payload to your LLM completion function (e.g., `agents/summarization_agent.py`)
        # Example of a simulated successful response:
        simulated_summary = (
            "The provided text outlines the new maintenance procedures, emphasizing "
            "the mandatory use of updated PPE and immediate reporting of track anomalies."
        )
        
        return SummarizeResponse(
            summary=simulated_summary,
            original_length_chars=len(payload.text),
            summary_length_chars=len(simulated_summary)
        )
        
    except Exception as exc:
        logger.error(f"Summarization pipeline failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.LLM_REQUEST_FAILED, 
                "message": "The summarization agent encountered an error."
            }
        )