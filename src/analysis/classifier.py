"""Document classification analysis service.

Scope: Wraps the ClassifierAgent to process full documents. Handles chunk 
sampling and result aggregation (e.g., majority voting) to determine the 
overall category of a large document without blowing up token limits.
"""

from __future__ import annotations

from collections import Counter
from typing import List

from config.logging import get_logger
from src.agents.classifier_agent import ClassifierAgent, ClassificationResult
from src.utils.constants import DocumentCategory

logger = get_logger(__name__)


class DocumentClassifierService:
    """Service to determine the overall category of a document."""

    def __init__(self, classifier_agent: ClassifierAgent) -> None:
        """Initializes the service with the underlying agent."""
        self.agent = classifier_agent

    def classify_document(self, text_chunks: List[str], sample_limit: int = 3) -> ClassificationResult:
        """Determines the document category by sampling its chunks.

        Args:
            text_chunks: A list of text chunks representing the document.
            sample_limit: The maximum number of chunks to evaluate (usually 
                the first few pages are enough to determine the category).

        Returns:
            A ClassificationResult representing the aggregated decision.
        """
        if not text_chunks:
            logger.warning("No text chunks provided for classification.")
            return ClassificationResult(
                category=DocumentCategory.GENERIC, 
                confidence=0.0, 
                reasoning="No text provided."
            )

        chunks_to_analyze = text_chunks[:sample_limit]
        results: List[ClassificationResult] = []

        for i, chunk in enumerate(chunks_to_analyze):
            try:
                logger.debug(f"Classifying chunk {i+1}/{len(chunks_to_analyze)}")
                res = self.agent.classify_text(chunk)
                results.append(res)
            except Exception as e:
                logger.warning(f"Failed to classify chunk {i}: {e}")

        if not results:
            return ClassificationResult(
                category=DocumentCategory.GENERIC, 
                confidence=0.0, 
                reasoning="All chunk classification attempts failed."
            )

        # Aggregate results using a simple majority vote
        category_counts = Counter(r.category for r in results)
        most_common_category, vote_count = category_counts.most_common(1)[0]
        
        # Calculate average confidence for the winning category
        winning_confidences = [r.confidence for r in results if r.category == most_common_category]
        avg_confidence = sum(winning_confidences) / len(winning_confidences) if winning_confidences else 0.0

        logger.info(f"Document classified as {most_common_category.name} with {avg_confidence:.2f} confidence.")

        return ClassificationResult(
            category=most_common_category,
            confidence=avg_confidence,
            reasoning=f"Majority vote ({vote_count}/{len(results)} chunks) determined this category."
        )