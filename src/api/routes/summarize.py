"""FastAPI router for text and document summarization.

Scope: Exposes endpoints to condense large texts or retrieved documents 
into concise summaries using the platform's LLM integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from config.logging import get_logger
from src.api.dependencies import get_summarizer_agent
from src.utils.constants import ErrorCode

if TYPE_CHECKING:
    from src.agents.summarizer_agent import SummarizerAgent

logger = get_logger(__name__)

router = APIRouter(prefix="/summarize", tags=["Summarization"])


class SummarizeTextRequest(BaseModel):
    """Schema for submitting raw text to be summarized."""
    text: str = Field(..., min_length=50, description="The full text content to summarize.")
    max_length_words: int = Field(default=150, ge=10, le=500, description="Target maximum word count for the summary.")
    focus_area: str | None = Field(default=None, description="Optional specific topic to focus the summary on.")

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class SummarizeResponse(BaseModel):
    """Schema for the summarization output."""
    summary: str
    key_points: List[str] = Field(default_factory=list)
    original_length_chars: int
    summary_length_chars: int


@router.post(
    "/text",
    response_model=SummarizeResponse,
    summary="Generate a summary for a provided text snippet"
)
async def summarize_text(
    payload: SummarizeTextRequest,
    agent: "SummarizerAgent" = Depends(get_summarizer_agent),
) -> SummarizeResponse:
    """Processes a raw text payload and returns a condensed summary.
    
    Can optionally accept a `focus_area` to tailor the summary (e.g., 
    'Summarize this text with a focus on safety protocols').
    """
    logger.info(f"Received summarization request (Text length: {len(payload.text)}, Focus: {payload.focus_area})")

    try:
        # Strict mode: an LLM or parse failure must surface as an error here, not as a
        # placeholder "summary" the caller would mistake for real output. The agent's call
        # blocks, so it runs in the threadpool.
        result = await run_in_threadpool(
            agent.generate_summary,
            payload.text,
            focus_area=payload.focus_area,
            max_words=payload.max_length_words,
            strict=True,
        )
    except ValueError as exc:
        logger.error(f"Summarization agent failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": ErrorCode.LLM_REQUEST_FAILED.value,
                "message": "The summarization agent failed to process the request."
            }
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Unexpected summarization failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred while summarizing the text."
            }
        ) from exc

    return SummarizeResponse(
        summary=result.summary,
        key_points=result.key_points,
        original_length_chars=len(payload.text),
        summary_length_chars=len(result.summary),
    )
