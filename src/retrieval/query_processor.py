"""
Query Processor and Text Normalization Module for the KMRL Retrieval Layer.

Provides deterministic cleaning, sanitization, and structural formatting of 
incoming user queries prior to index lookup execution.
"""

import logging
import re
from typing import List

logger = logging.getLogger("document_intelligence.retrieval.query_processor")


class QueryProcessor:
    """
    Handles the sanitization and structural conditioning of inbound query strings.
    """

    def __init__(self, lower_case: bool = True, strip_punctuation: bool = True) -> None:
        """
        Initializes the query processing rules.

        Args:
            lower_case: If True, normalizes all text queries to lowercase.
            strip_punctuation: If True, cleans characters that interfere with lexical search indexes.
        """
        self.lower_case = lower_case
        self.strip_punctuation = strip_punctuation
        # Match standard punctuation characters except alphanumeric spaces
        self.punctuation_pattern = re.compile(r"[^\w\s\-]")
        # Match redundant whitespace/tab/newline blocks
        self.whitespace_pattern = re.compile(r"\s+")
        
        logger.info(
            f"QueryProcessor initialized with rules -> lowercase: {self.lower_case}, "
            f"strip_punctuation: {self.strip_punctuation}"
        )

    def process(self, raw_query: str) -> str:
        """
        Applies configured sanitization routines to an incoming raw text query.

        Args:
            raw_query: The unfiltered query string directly from the API router layer.

        Returns:
            A sanitized, single-line, normalized query string.
        """
        if not raw_query:
            return ""

        # Step 1: Uniform string trimming
        cleaned_query = raw_query.strip()

        # Step 2: Conditional case normalization
        if self.lower_case:
            cleaned_query = cleaned_query.lower()

        # Step 3: Strip noisy punctuation marks that break lexical matching tokens
        if self.strip_punctuation:
            cleaned_query = self.punctuation_pattern.sub(" ", cleaned_query)

        # Step 4: Condense multiple spaces/tabs/newlines into a single uniform spacing character
        cleaned_query = self.whitespace_pattern.sub(" ", cleaned_query).strip()

        logger.debug(f"Query processed successfully. Original: '{raw_query}' -> Output: '{cleaned_query}'")
        return cleaned_query

    def extract_keywords(self, processed_query: str) -> List[str]:
        """
        Utility method to split a processed query string into individual distinct tokens.
        Particularly useful for downstream BM25 or keyword frequency matching steps.
        """
        if not processed_query:
            return []
        return [token for token in processed_query.split(" ") if token]