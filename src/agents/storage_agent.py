"""Storage and Routing Agent for the KMRL platform.

Scope: Interfaces with the LLM to evaluate text chunks prior to database 
insertion. It determines whether the text contains enough meaningful 
information to be stored and recommends the appropriate database collection 
or namespace for optimal retrieval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Any, List

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StorageDecision:
    """Structured output containing the routing and storage decision."""
    should_store: bool
    primary_collection: str
    tags: List[str] = field(default_factory=list)
    reasoning: str = ""


class StorageAgent:
    """Agent responsible for evaluating and routing documents for storage.

    Uses a strict system prompt to act as a data governance filter, 
    ensuring low-quality or irrelevant text isn't indexed, and categorizing 
    valid text into predefined storage collections.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the StorageAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        # Predefined allowed collections in your vector database
        self._valid_collections = ["safety_manuals", "maintenance_logs", "hr_policies", "general_knowledge", "discard"]
        
        self._system_prompt = (
            "You are an expert data governance and routing system. Your task is to evaluate "
            "the provided text and determine if it contains meaningful, indexable information, "
            "and decide which database collection it belongs in.\n\n"
            f"ALLOWED COLLECTIONS: {self._valid_collections}\n\n"
            "RULES:\n"
            "1. Output your response in strictly valid JSON format.\n"
            "2. Set 'should_store' to true ONLY if the text has coherent, useful information. "
            "If it is gibberish, highly fragmented, or completely empty, set to false.\n"
            "3. The 'primary_collection' must exactly match one of the ALLOWED COLLECTIONS. "
            "If 'should_store' is false, set the collection to 'discard'.\n"
            "4. Provide 1 to 3 categorization 'tags' as a list of strings.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "should_store": boolean,\n'
            '  "primary_collection": "string",\n'
            '  "tags": ["string", "string"],\n'
            '  "reasoning": "string"\n'
            "}"
        )
        logger.debug(f"StorageAgent initialized with collections: {self._valid_collections}")

    def evaluate_for_storage(self, text: str) -> StorageDecision:
        """Evaluates the text and determines its optimal storage routing.

        Args:
            text: The raw document text or chunk to evaluate.

        Returns:
            A StorageDecision dataclass containing the routing instructions.
        """
        if not text or len(text.strip()) < 10:
            logger.warning("StorageAgent received empty or extremely short text. Rejecting storage.")
            return StorageDecision(
                should_store=False, 
                primary_collection="discard", 
                reasoning="Text was empty or too short to contain meaningful information."
            )

        user_prompt = f"--- TEXT TO EVALUATE ---\n{text}\n\nDetermine storage routing."
        
        try:
            logger.debug(f"Dispatching storage evaluation request (Text length: {len(text)}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"StorageAgent execution failed: {exc}")
            # Fail safe: default to storing in general knowledge to avoid data loss
            return StorageDecision(
                should_store=True,
                primary_collection="general_knowledge",
                tags=["error_fallback"],
                reasoning=f"Agent exception occurred: {exc}. Defaulting to general storage."
            )

    def _parse_response(self, response_text: str) -> StorageDecision:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            should_store = bool(parsed_data.get("should_store", True))
            collection = str(parsed_data.get("primary_collection", "general_knowledge")).lower()
            
            if collection not in self._valid_collections:
                logger.warning(f"LLM returned invalid collection '{collection}'. Defaulting to 'general_knowledge'.")
                collection = "general_knowledge"

            tags = parsed_data.get("tags", [])
            if not isinstance(tags, list):
                tags = [str(tags)]

            return StorageDecision(
                should_store=should_store,
                primary_collection=collection,
                tags=[str(t) for t in tags],
                reasoning=str(parsed_data.get("reasoning", "No reasoning provided."))
            )

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse LLM storage routing response: {exc}. Raw: {response_text}")
            return StorageDecision(
                should_store=True,
                primary_collection="general_knowledge",
                tags=["parse_error"],
                reasoning="JSON parsing failed. Defaulting to general storage."
            )