"""RAG Answer-Generation Manager for the KMRL Platform.

Wraps the low-level :class:`~src.llm.llm_client.LLMClient` with retrieval-augmented
generation concerns: it stitches retrieved context chunks into a grounded prompt,
invokes the model, and returns a structured :class:`GeneratedAnswer` that carries the
answer text together with the exact context chunks used (for citations) and any
generation telemetry.

This module was referenced by ``chat_pipeline`` and ``graph_pipeline`` but did not
previously exist; it is the concrete implementation of that contract.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config.logging import get_logger
from src.llm.llm_client import LLMClient, LLMClientConfig
from src.vector_store.base import SearchResult

logger = get_logger(__name__)


DEFAULT_SYSTEM_PROMPT = (
    "You are the KMRL Document Intelligence assistant. Answer the user's question "
    "using ONLY the provided context passages. If the context is insufficient, say so "
    "plainly instead of inventing facts. Cite the source filenames you rely on."
)


class GeneratedAnswer(BaseModel):
    """Structured result of a single answer-generation pass."""

    model_config = {"arbitrary_types_allowed": True}

    answer: str = Field(..., description="The synthesized natural-language answer.")
    context_chunks: List[SearchResult] = Field(
        default_factory=list,
        description="The retrieved chunks used as grounding context (for citations).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation telemetry (e.g. token_usage, model name).",
    )


class LLMManager:
    """High-level orchestrator turning a query + context into a grounded answer."""

    def __init__(
        self,
        client: Optional[LLMClient] = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.client = client or LLMClient(LLMClientConfig())
        self.system_prompt = system_prompt
        logger.debug("LLMManager initialized.")

    @staticmethod
    def _format_context(context_chunks: List[SearchResult]) -> str:
        if not context_chunks:
            return "No context passages were retrieved."
        blocks: List[str] = []
        for i, chunk in enumerate(context_chunks, start=1):
            source = chunk.metadata.get("filename", chunk.metadata.get("document_id", "unknown"))
            blocks.append(f"[{i}] (source: {source})\n{chunk.text}")
        return "\n\n".join(blocks)

    def generate_answer(
        self,
        query: str,
        context_chunks: List[SearchResult],
    ) -> GeneratedAnswer:
        """Generate a grounded answer for ``query`` using ``context_chunks``.

        Args:
            query: The (possibly history-augmented) user question.
            context_chunks: Retrieved passages that ground the answer.

        Returns:
            A :class:`GeneratedAnswer` carrying the text, the context, and telemetry.
        """
        context_block = self._format_context(context_chunks)
        user_prompt = (
            f"Context passages:\n{context_block}\n\n"
            f"Question:\n{query}\n\n"
            f"Answer:"
        )

        logger.info("Generating grounded answer over %d context chunks.", len(context_chunks))
        answer_text = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )

        return GeneratedAnswer(
            answer=answer_text.strip(),
            context_chunks=context_chunks,
            metadata={"model": self.client.config.model_name},
        )
