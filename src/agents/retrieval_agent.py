"""Retrieval and Synthesis Agent for the KMRL platform.

Scope: Synthesizes final answers to user queries using strictly the 
context retrieved from the vector database. It prevents hallucinations 
by explicitly evaluating whether the provided context contains the answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Any

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SynthesisResult:
    """Structured output containing the generated answer and confidence flag."""
    answer: str
    is_grounded: bool
    reasoning: str


class RetrievalAgent:
    """Agent responsible for grounded question-answering.

    This agent receives context chunks and a user query, constructing a strict 
    prompt that forces the LLM to rely solely on the provided text, mitigating 
    the risk of hallucinated information.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the RetrievalAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        self._system_prompt = (
            "You are an expert technical assistant for the KMRL platform. Your task is to "
            "answer the user's question using strictly the information provided in the 'CONTEXT' block.\n\n"
            "RULES:\n"
            "1. Output your response in strictly valid JSON format.\n"
            "2. If the answer cannot be found in the context, do NOT guess or make up information. "
            "Set 'is_grounded' to false and state 'The provided context does not contain the answer' in the 'answer' field.\n"
            "3. If the answer is found, provide a clear, professional response in the 'answer' field and set 'is_grounded' to true.\n"
            "4. Use the 'reasoning' field to briefly explain how the context supports the answer (or lack thereof).\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "answer": "string",\n'
            '  "is_grounded": boolean,\n'
            '  "reasoning": "string"\n'
            "}"
        )
        logger.debug("RetrievalAgent initialized.")

    def synthesize_answer(self, query: str, context: str) -> SynthesisResult:
        """Generates a final answer based on the retrieved context.

        Args:
            query: The user's original question.
            context: The aggregated text chunks retrieved from the vector database.

        Returns:
            A SynthesisResult dataclass containing the answer and grounding flag.
        """
        if not context or not context.strip():
            logger.warning("RetrievalAgent received empty context. Forcing ungrounded response.")
            return SynthesisResult(
                answer="No relevant context was found to answer this query.",
                is_grounded=False,
                reasoning="Empty context provided."
            )

        user_prompt = (
            f"--- CONTEXT ---\n{context}\n\n"
            f"--- QUESTION ---\n{query}\n\n"
            "Generate the answer based on the rules."
        )
        
        try:
            logger.debug(f"Dispatching synthesis request for query: '{query}'")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"RetrievalAgent execution failed: {exc}")
            return SynthesisResult(
                answer="An error occurred while generating the response.",
                is_grounded=False,
                reasoning=f"Agent exception: {exc}"
            )

    def _parse_response(self, response_text: str) -> SynthesisResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            # Safely extract boolean
            is_grounded_raw = parsed_data.get("is_grounded", False)
            is_grounded = bool(is_grounded_raw) if isinstance(is_grounded_raw, (bool, int)) else False

            return SynthesisResult(
                answer=str(parsed_data.get("answer", "Failed to extract answer from model output.")),
                is_grounded=is_grounded,
                reasoning=str(parsed_data.get("reasoning", "No reasoning provided."))
            )

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse LLM retrieval response: {exc}. Raw: {response_text}")
            return SynthesisResult(
                answer="The system encountered an error parsing the underlying model's response.",
                is_grounded=False,
                reasoning="JSON parse error."
            )