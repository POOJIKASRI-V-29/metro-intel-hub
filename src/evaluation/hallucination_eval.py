"""Hallucination detection and grounding evaluation for the KMRL platform.

Scope: Evaluates whether a generated answer introduces claims, facts, or 
entities not present in the provided context window. This relies on an 
LLM-as-a-judge approach to perform semantic entailment checks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HallucinationEvaluationResult:
    """Structured output containing the results of a hallucination check."""
    is_hallucinated: bool
    grounding_score: float  # 0.0 (completely hallucinated) to 1.0 (fully grounded)
    reasoning: str


class HallucinationEvaluator:
    """Evaluates answer grounding using a designated Large Language Model.

    This evaluator constructs a strict prompt asking an LLM to act as a 
    fact-checker. It determines if the generated answer is entirely 
    supported by the provided context.
    """

    # The system prompt enforces strict JSON output to guarantee reliable parsing
    _EVALUATION_SYSTEM_PROMPT = (
        "You are an impartial, rigorous fact-checking system. Your task is to determine "
        "if the provided 'Generated Answer' is fully supported by the 'Source Context'.\n\n"
        "RULES:\n"
        "1. If the answer contains ANY facts, names, or claims not found in the context, it is a hallucination.\n"
        "2. If the answer says 'I don't know' because the context lacks information, that is NOT a hallucination (grounded).\n"
        "3. Output your evaluation strictly in valid JSON format matching the following schema:\n"
        "{\n"
        '  "is_hallucinated": boolean,\n'
        '  "grounding_score": float (0.0 to 1.0),\n'
        '  "reasoning": string (brief explanation referencing specific claims)\n'
        "}"
    )

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the hallucination evaluator.

        Args:
            llm_generate_fn: A callable that takes a (system_prompt, user_prompt) 
                and returns a text response from the LLM. Dependency injection 
                is used here to keep this module decoupled from specific LLM SDKs.
        """
        self.llm_generate = llm_generate_fn
        logger.debug("HallucinationEvaluator initialized with injected LLM callable.")

    def evaluate(self, retrieved_context: str, generated_answer: str) -> HallucinationEvaluationResult:
        """Evaluates an answer against its context for factual consistency.

        Args:
            retrieved_context: The raw text context provided to the RAG pipeline.
            generated_answer: The final answer produced by the generation model.

        Returns:
            A HallucinationEvaluationResult detailing the factual grounding.
            
        Raises:
            ValueError: If the input strings are entirely empty.
        """
        if not retrieved_context.strip():
            logger.warning("Evaluating hallucination with empty context. Any factual answer will be flagged.")
        if not generated_answer.strip():
            raise ValueError("Cannot evaluate an empty generated answer.")

        user_prompt = (
            f"--- SOURCE CONTEXT ---\n{retrieved_context}\n\n"
            f"--- GENERATED ANSWER ---\n{generated_answer}\n\n"
            "Evaluate the answer based ONLY on the source context."
        )

        try:
            logger.debug("Dispatching hallucination evaluation prompt to LLM.")
            raw_response = self.llm_generate(self._EVALUATION_SYSTEM_PROMPT, user_prompt)
            return self._parse_evaluation_response(raw_response)
        except Exception as exc:
            logger.error(f"Hallucination evaluation failed during LLM execution: {exc}")
            # Fail closed: If the evaluator crashes, assume the answer is unsafe/hallucinated
            return HallucinationEvaluationResult(
                is_hallucinated=True,
                grounding_score=0.0,
                reasoning=f"Evaluation failed due to internal error: {exc}"
            )

    def _parse_evaluation_response(self, response_text: str) -> HallucinationEvaluationResult:
        """Safely extracts the JSON payload from the LLM's raw string response."""
        # Strip potential markdown formatting (e.g., ```json ... ```)
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data = json.loads(clean_text.strip())
            
            # Validate expected keys exist
            if not all(key in parsed_data for key in ("is_hallucinated", "grounding_score", "reasoning")):
                raise KeyError("Missing required keys in LLM JSON response.")

            return HallucinationEvaluationResult(
                is_hallucinated=bool(parsed_data["is_hallucinated"]),
                grounding_score=float(parsed_data["grounding_score"]),
                reasoning=str(parsed_data["reasoning"])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error(f"Failed to parse LLM evaluation response: {exc}. Raw response: {response_text}")
            return HallucinationEvaluationResult(
                is_hallucinated=True,
                grounding_score=0.0,
                reasoning="Failed to parse evaluator output."
            )