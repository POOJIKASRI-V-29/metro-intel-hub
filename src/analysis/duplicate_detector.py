"""Algorithmic duplicate detection service.

Scope: Provides exact-match and near-match deduplication logic to prevent 
re-ingesting the same files into the vector and graph databases, saving 
compute costs and avoiding redundant search results.
"""

from __future__ import annotations

import hashlib
from typing import Set

from config.logging_config import get_logger

logger = get_logger(__name__)


class DuplicateDetector:
    """Service to detect duplicate documents or text chunks."""

    @staticmethod
    def compute_exact_hash(text: str) -> str:
        """Computes a SHA-256 hash of the normalized text.

        Args:
            text: The raw string content of the document.

        Returns:
            A hex string representing the hash.
        """
        if not text:
            return ""
            
        # Normalize whitespace and casing for a more robust hash
        normalized = " ".join(text.split()).lower().encode('utf-8')
        return hashlib.sha256(normalized).hexdigest()

    def is_exact_duplicate(self, text: str, existing_hashes: Set[str]) -> bool:
        """Checks if the exact text content has already been processed.

        Args:
            text: The text to evaluate.
            existing_hashes: A set of known document hashes (usually fetched from a DB).

        Returns:
            True if a duplicate is found, False otherwise.
        """
        if not text or not existing_hashes:
            return False
            
        doc_hash = self.compute_exact_hash(text)
        is_dup = doc_hash in existing_hashes
        
        if is_dup:
            logger.info(f"Duplicate detected via exact hash match: {doc_hash[:8]}...")
            
        return is_dup

    # Note: For Post-MVP, you could add semantic deduplication here 
    # using MinHash, SimHash, or fast cosine similarity on small embeddings.