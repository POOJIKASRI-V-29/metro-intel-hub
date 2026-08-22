"""Document summarization analysis service.

Scope: Wraps the SummarizerAgent to process full documents. Handles 
large documents by employing a map-reduce summarization strategy (chunk 
summaries combined into a master summary) to avoid token limit exceptions.
"""

from __future__ import annotations

from typing import List, Optional

from config.logging_config import get_logger
from agents.summarizer_agent import SummarizerAgent, SummaryResult

logger = get_logger(__name__)


class DocumentSummarizerService:
    """Service to generate a cohesive summary of a full document."""

    def __init__(self, summarizer_agent: SummarizerAgent) -> None:
        """Initializes the service with the underlying agent."""
        self.agent = summarizer_agent

    def summarize_document(self, text_chunks: List[str], focus_area: Optional[str] = None) -> SummaryResult:
        """Generates a comprehensive summary across all text chunks.

        Uses a map-reduce pattern for multi-chunk documents:
        1. Map: Summarize each chunk individually.
        2. Reduce: Concatenate chunk summaries and summarize the result.

        Args:
            text_chunks: A list of text chunks representing the document.
            focus_area: An optional specific topic to tailor the summary around.

        Returns:
            A SummaryResult containing the final master summary and key points.
        """
        if not text_chunks:
            logger.warning("No text chunks provided for summarization.")
            return SummaryResult(summary="No text provided to summarize.")

        if len(text_chunks) == 1:
            # Single chunk: summarize directly
            logger.debug("Single chunk document detected. Summarizing directly.")
            return self.agent.generate_summary(text_chunks[0], focus_area)

        # Map phase: Summarize each chunk
        logger.info(f"Starting map-reduce summarization for {len(text_chunks)} chunks.")
        chunk_summaries: List[str] = []
        all_key_points: List[str] = []

        for i, chunk in enumerate(text_chunks):
            try:
                logger.debug(f"Summarizing chunk {i+1}/{len(text_chunks)}")
                res = self.agent.generate_summary(chunk, focus_area)
                chunk_summaries.append(res.summary)
                all_key_points.extend(res.key_points)
            except Exception as e:
                logger.error(f"Failed to summarize chunk {i}: {e}")

        if not chunk_summaries:
            return SummaryResult(summary="Failed to generate any chunk summaries.")

        # Reduce phase: Combine and summarize the summaries
        master_text = " ".join(chunk_summaries)
        logger.debug(f"Generating master summary from combined chunk summaries (length: {len(master_text)}).")
        
        try:
            final_result = self.agent.generate_summary(master_text, focus_area)
            
            # Optionally merge key points from the chunks if the final agent missed some
            if len(final_result.key_points) < 3 and all_key_points:
                # Deduplicate and take the top few from the map phase
                unique_points = list(dict.fromkeys(all_key_points))
                final_result.key_points = unique_points[:5]
                
            return final_result
            
        except Exception as e:
            logger.error(f"Failed to generate master summary: {e}")
            return SummaryResult(
                summary="Master summary generation failed. Returning combined chunk summaries instead. " + master_text[:500] + "...",
                key_points=list(dict.fromkeys(all_key_points))[:5]
            )