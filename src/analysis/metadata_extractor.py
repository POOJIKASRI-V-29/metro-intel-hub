"""Document metadata extraction service.

Scope: Wraps the MetadataAgent. Manages the extraction of global document 
metadata by focusing on the beginning of documents where titles, authors, 
and dates are typically located.
"""

from __future__ import annotations

from typing import List

from config.logging_config import get_logger
from agents.metadata_agent import MetadataAgent, MetadataExtractionResult

logger = get_logger(__name__)


class DocumentMetadataService:
    """Service to extract and normalize global document metadata."""

    def __init__(self, metadata_agent: MetadataAgent) -> None:
        """Initializes the service with the underlying agent."""
        self.agent = metadata_agent

    def extract_document_metadata(self, text_chunks: List[str]) -> MetadataExtractionResult:
        """Extracts metadata from the first chunk of a document.

        Args:
            text_chunks: A list of text chunks representing the document.

        Returns:
            A MetadataExtractionResult containing the parsed fields.
        """
        if not text_chunks:
            logger.warning("No text chunks provided for metadata extraction.")
            return MetadataExtractionResult(
                title="Unknown", 
                author="Unknown", 
                creation_date="Unknown"
            )

        # Metadata is almost always in the first chunk (title page, headers)
        head_chunk = text_chunks[0]
        
        logger.debug(f"Extracting metadata from head chunk (length: {len(head_chunk)})")
        
        try:
            result = self.agent.extract_metadata(head_chunk)
            return self._normalize_metadata(result)
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return MetadataExtractionResult(
                title="Unknown", 
                author="Unknown", 
                creation_date="Unknown"
            )

    def _normalize_metadata(self, raw_result: MetadataExtractionResult) -> MetadataExtractionResult:
        """Applies business rules to clean up the LLM output."""
        # Clean up titles that might have extra quotes
        if raw_result.title and raw_result.title.startswith('"') and raw_result.title.endswith('"'):
            raw_result.title = raw_result.title[1:-1]

        # Limit keywords to prevent massive index bloat
        if len(raw_result.keywords) > 10:
            raw_result.keywords = raw_result.keywords[:10]
            
        # Lowercase keywords for standardized filtering
        raw_result.keywords = [k.lower() for k in raw_result.keywords]

        return raw_result