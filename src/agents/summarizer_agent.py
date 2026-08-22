"""Summarization Agent for the KMRL platform.

Scope: Interfaces with the LLM to condense large bodies of text into 
concise summaries and extract key bullet points. Supports focus-driven 
summarization for targeted insights.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Any, List, Optional

from config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SummaryResult:
    """Structured output containing the summary and key extracted points."""
    summary: str
    key_points: List[str] = field(default_factory=list)


class SummarizerAgent:
    """Agent responsible for generating text summaries.

    Uses prompt engineering to enforce a specific length constraint (conceptually) 
    and forces the LLM to output a structured JSON object containing a paragraph 
    summary and a list of core bullet points.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the SummarizerAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        self._system_prompt = (
            "You are an expert technical writer and summarization AI. Your task is to condense "
            "the provided text into a clear, concise summary.\n\n"
            "RULES:\n"
            "1. Output your response in strictly valid JSON format.\n"
            "2. The 'summary' field should be a single, cohesive paragraph.\n"
            "3. The 'key_points' field must be an array of 3 to 5 brief strings highlighting the most important details.\n"
            "4. If a 'FOCUS AREA' is provided, tailor the summary to highlight information relevant to that area.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "key_points": ["string", "string"]\n'
            "}"
        )
        logger.debug("SummarizerAgent initialized.")

    def generate_summary(self, text: str, focus_area: Optional[str] = None) -> SummaryResult:
        """Generates a summary of the provided text.

        Args:
            text: The raw document text to summarize.
            focus_area: An optional specific topic to tailor the summary around.

        Returns:
            A SummaryResult dataclass containing the summary and key points.
        """
        if not text or not text.strip():
            logger.warning("SummarizerAgent received empty text. Returning empty summary.")
            return SummaryResult(summary="No text provided to summarize.")

        user_prompt = f"--- TEXT TO SUMMARIZE ---\n{text}\n\n"
        if focus_area:
            user_prompt += f"--- FOCUS AREA ---\n{focus_area}\n\n"
            
        user_prompt += "Generate the summary and key points."
        
        try:
            logger.debug(f"Dispatching summarization request (Text length: {len(text)}, Focus: {focus_area}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"SummarizerAgent execution failed: {exc}")
            return SummaryResult(
                summary="An error occurred while attempting to summarize the text.",
                key_points=[f"Error: {exc}"]
            )

    def _parse_response(self, response_text: str) -> SummaryResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            summary = str(parsed_data.get("summary", "No summary generated."))
            
            key_points_raw = parsed_data.get("key_points", [])
            if not isinstance(key_points_raw, list):
                key_points_raw = [str(key_points_raw)]
            
            key_points = [str(kp) for kp in key_points_raw if str(kp).strip()]

            return SummaryResult(
                summary=summary,
                key_points=key_points
            )

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse LLM summarization response: {exc}. Raw: {response_text}")
            return SummaryResult(
                summary="The system encountered an error parsing the underlying model's response.",
                key_points=["JSON parsing failure."]
            )