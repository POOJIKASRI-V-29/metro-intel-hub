"""Classification Agent for the KMRL platform.

Scope: Interfaces with the LLM to classify documents or text snippets 
into a strict, predefined set of categories. This agent constructs the 
necessary system prompts, enforces JSON output schemas, and parses 
the results back into usable Python data types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Any

from config.logging_config import get_logger
from utils.constants import DocumentCategory

logger = get_logger(__name__)


@dataclass
class ClassificationResult:
    """Structured output containing the agent's classification decision."""
    category: DocumentCategory
    confidence: float
    reasoning: str


class ClassifierAgent:
    """Agent responsible for categorizing text using a Large Language Model.

    This class encapsulates the prompt engineering and output parsing required 
    to force an LLM into a deterministic classification task.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the ClassifierAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM. Dependency injection 
                is used here to remain model-agnostic.
        """
        self.llm_generate = llm_generate_fn
        self._valid_categories = [category.value for category in DocumentCategory]
        
        self._system_prompt = (
            "You are an expert document classification system. Your task is to categorize "
            "the provided text into exactly ONE of the following approved categories:\n"
            f"{self._valid_categories}\n\n"
            "RULES:\n"
            "1. You must output your response in strictly valid JSON format.\n"
            "2. The 'category' field must exactly match one of the approved categories.\n"
            "3. The 'confidence' field must be a float between 0.0 and 1.0.\n"
            "4. The 'reasoning' field should briefly explain the decision.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "category": "string",\n'
            '  "confidence": float,\n'
            '  "reasoning": "string"\n'
            "}"
        )
        logger.debug("ClassifierAgent initialized with available categories.")

    def classify_text(self, text: str) -> ClassificationResult:
        """Analyzes the text and assigns it to a canonical DocumentCategory.

        Args:
            text: The raw document text or chunk to classify.

        Returns:
            A ClassificationResult dataclass containing the structured decision.
            
        Raises:
            ValueError: If the text is empty or the agent fails to parse the output.
        """
        if not text or not text.strip():
            logger.error("ClassifierAgent received empty text for classification.")
            raise ValueError("Cannot classify empty text.")

        user_prompt = f"--- TEXT TO CLASSIFY ---\n{text}\n\nAnalyze and classify the text."
        
        try:
            logger.debug(f"Dispatching classification request (Text length: {len(text)}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"ClassifierAgent execution failed: {exc}")
            # Fail gracefully to an 'UNKNOWN' or 'OTHER' category if one exists in your enum,
            # or re-raise if classification is a strict requirement.
            raise ValueError(f"Agent failed to classify text: {exc}") from exc

    def _parse_response(self, response_text: str) -> ClassificationResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        # Strip common markdown code block wrappers
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            raw_category = parsed_data.get("category", "")
            confidence = float(parsed_data.get("confidence", 0.0))
            reasoning = str(parsed_data.get("reasoning", "No reasoning provided."))

            # Validate that the model returned a supported category string
            try:
                category_enum = DocumentCategory(raw_category)
            except ValueError:
                logger.warning(f"LLM returned invalid category '{raw_category}'. Defaulting to GENERIC.")
                category_enum = DocumentCategory.GENERIC # Assuming you have a fallback

            return ClassificationResult(
                category=category_enum,
                confidence=max(0.0, min(1.0, confidence)), # Bound between 0 and 1
                reasoning=reasoning
            )

        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.error(f"Failed to parse LLM classification response: {exc}. Raw: {response_text}")
            raise ValueError("Invalid JSON structure returned by LLM.") from exc