"""Metadata Extraction Agent for the KMRL platform.

Scope: Interfaces with the LLM to extract structural metadata from raw 
document text. This includes identifying the document's title, primary 
author, creation date, and relevant keywords to enrich the vector store 
and knowledge graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Any, List

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetadataExtractionResult:
    """Structured output containing the extracted document metadata."""
    title: str
    author: str
    creation_date: str
    keywords: List[str] = field(default_factory=list)
    document_type: str = "Unknown"


class MetadataAgent:
    """Agent responsible for parsing metadata from unstructured text.

    Constructs strict prompts to force the LLM to act as an information 
    extraction tool, ensuring output matches a predictable JSON schema.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the MetadataAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        self._system_prompt = (
            "You are an expert document analysis system. Your task is to extract "
            "standard metadata from the provided document text.\n\n"
            "RULES:\n"
            "1. Output your response in strictly valid JSON format.\n"
            "2. If a specific piece of metadata is not found in the text, return 'Unknown' for strings or an empty list for arrays.\n"
            "3. 'creation_date' should be formatted as YYYY-MM-DD if possible. Otherwise, extract the exact date string found.\n"
            "4. Extract 3 to 7 highly relevant 'keywords' as a list of strings.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "title": "string",\n'
            '  "author": "string",\n'
            '  "creation_date": "string",\n'
            '  "keywords": ["string", "string"],\n'
            '  "document_type": "string"\n'
            "}"
        )
        logger.debug("MetadataAgent initialized.")

    def extract_metadata(self, text: str) -> MetadataExtractionResult:
        """Analyzes the text to extract core metadata fields.

        Args:
            text: The raw document text (usually the first few pages/chunks 
                where metadata is most likely located).

        Returns:
            A MetadataExtractionResult dataclass containing the parsed fields.
        """
        if not text or not text.strip():
            logger.warning("MetadataAgent received empty text. Returning default metadata.")
            return MetadataExtractionResult(title="Unknown", author="Unknown", creation_date="Unknown")

        user_prompt = f"--- DOCUMENT TEXT ---\n{text}\n\nExtract the metadata."
        
        try:
            logger.debug(f"Dispatching metadata extraction request (Text length: {len(text)}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"MetadataAgent execution failed: {exc}")
            # Fail closed to prevent pipeline crashes
            return MetadataExtractionResult(title="Unknown", author="Unknown", creation_date="Unknown")

    def _parse_response(self, response_text: str) -> MetadataExtractionResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            # Ensure keywords is always a list
            keywords = parsed_data.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = [str(keywords)]

            return MetadataExtractionResult(
                title=str(parsed_data.get("title", "Unknown")),
                author=str(parsed_data.get("author", "Unknown")),
                creation_date=str(parsed_data.get("creation_date", "Unknown")),
                keywords=[str(k) for k in keywords],
                document_type=str(parsed_data.get("document_type", "Unknown"))
            )

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse LLM metadata response: {exc}. Raw: {response_text}")
            return MetadataExtractionResult(title="Unknown", author="Unknown", creation_date="Unknown")