"""RAGAS-inspired evaluation metrics for the KMRL platform.

Scope: Evaluates the quality of RAG generations using LLM-as-a-judge methods.
Focuses on 'Faithfulness' (how well the answer is grounded in the context) 
and 'Answer Relevance' (how well the answer addresses the original user query).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RagasEvaluationResult:
    """Structured output containing RAGAS metric scores."""
    faithfulness_score: float  # 0.0 to 1.0
    answer_relevance_score: float  # 0.0 to 1.0
    faithfulness_reasoning: str
    relevance_reasoning: str


class RagasEvaluator:
    """Evaluates generation quality using RAGAS methodologies.

    This evaluator dispatches specific prompts to an LLM to score the 
    faithfulness of an answer to its context, and the relevance of that 
    answer to the initial query.
    """

    _FAITHFULNESS_SYSTEM_PROMPT = (
        "You are an expert fact-checker. Given a 'Context' and an 'Answer', "
        "determine the Faithfulness score of the Answer. \n"
        "Faithfulness measures how much of the Answer is inferred strictly from the Context. "
        "Score 1.0 if all claims are supported. Score 0.0 if no claims are supported or if it hallucinates. "
        "Partial scores (e.g., 0.5) are allowed for partially supported answers.\n\n"
        "Output strictly valid JSON:\n"
        "{\n"
        '  "score": float,\n'
        '  "reasoning": string\n'
        "}"
    )

    _RELEVANCE_SYSTEM_PROMPT = (
        "You are an expert evaluator. Given a 'Question' and an 'Answer', "
        "determine the Answer Relevance score. \n"
        "Answer Relevance measures how directly and accurately the Answer addresses the Question. "
        "Score 1.0 if it perfectly answers the question. Score 0.0 if it is evasive, off-topic, or fails to address the core intent.\n\n"
        "Output strictly valid JSON:\n"
        "{\n"
        '  "score": float,\n'
        '  "reasoning": string\n'
        "}"
    )

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the RAGAS evaluator.

        Args:
            llm_generate_fn: A callable taking (system_prompt, user_prompt) 
                that returns the LLM's text response.
        """
        self.llm_generate = llm_generate_fn
        logger.debug("RagasEvaluator initialized with injected LLM callable.")

    def evaluate(self, query: str, context: str, generated_answer: str) -> RagasEvaluationResult:
        """Runs both Faithfulness and Answer Relevance evaluations.

        Args:
            query: The original user question.
            context: The retrieved text context.
            generated_answer: The final generated response.

        Returns:
            A RagasEvaluationResult containing scores and reasoning.
        """
        if not generated_answer.strip():
            logger.warning("Empty generated answer provided to RAGAS evaluator.")
            return RagasEvaluationResult(0.0, 0.0, "Empty answer.", "Empty answer.")

        # 1. Evaluate Faithfulness (Answer vs Context)
        faithfulness_data = self._evaluate_metric(
            system_prompt=self._FAITHFULNESS_SYSTEM_PROMPT,
            user_prompt=f"--- CONTEXT ---\n{context}\n\n--- ANSWER ---\n{generated_answer}"
        )

        # 2. Evaluate Answer Relevance (Answer vs Query)
        relevance_data = self._evaluate_metric(
            system_prompt=self._RELEVANCE_SYSTEM_PROMPT,
            user_prompt=f"--- QUESTION ---\n{query}\n\n--- ANSWER ---\n{generated_answer}"
        )

        return RagasEvaluationResult(
            faithfulness_score=faithfulness_data.get("score", 0.0),
            faithfulness_reasoning=faithfulness_data.get("reasoning", "Failed to evaluate."),
            answer_relevance_score=relevance_data.get("score", 0.0),
            relevance_reasoning=relevance_data.get("reasoning", "Failed to evaluate.")
        )

    def _evaluate_metric(self, system_prompt: str, user_prompt: str) -> dict[str, any]:
        """Dispatches a specific evaluation prompt and parses the JSON result."""
        try:
            raw_response = self.llm_generate(system_prompt, user_prompt)
            return self._parse_json_response(raw_response)
        except Exception as exc:
            logger.error(f"LLM evaluation request failed: {exc}")
            return {"score": 0.0, "reasoning": f"Execution error: {exc}"}

    def _parse_json_response(self, response_text: str) -> dict[str, any]:
        """Safely extracts and validates the JSON payload from the LLM."""
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed = json.loads(clean_text.strip())
            
            # Ensure types are correct
            score = float(parsed.get("score", 0.0))
            reasoning = str(parsed.get("reasoning", "No reasoning provided."))
            
            # Bound the score between 0.0 and 1.0
            score = max(0.0, min(1.0, score))
            
            return {"score": score, "reasoning": reasoning}
            
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"Failed to parse JSON from LLM: {exc}. Raw: {response_text}")
            return {"score": 0.0, "reasoning": "JSON parse error."}