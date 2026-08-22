"""Retrieval-Augmented Generation (RAG) pipeline for the KMRL platform.

Scope: Orchestrates the end-to-end question-answering workflow by combining 
vector search retrieval with LLM response generation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from config.logging import get_logger
from config.prompts import PromptName, render_prompt
from src.embeddings.manager import EmbeddingManager
from src.llm.llm_client import LLMClient
from src.utils.logger import log_execution_time

logger = get_logger(__name__)


class RAGPipeline:
    """Coordinates vector search and LLM generation for grounded QA."""

    def __init__(self, vector_db_client: Any = None) -> None:
        """Initializes the RAG pipeline and its dependencies.

        Args:
            vector_db_client: The initialized client for your vector database 
                (e.g., Qdrant, Milvus). Passed via dependency injection.
        """
        logger.info("Initializing RAG Pipeline orchestration...")
        self.embedding_manager = EmbeddingManager()
        self.llm_client = LLMClient()
        self.vector_db = vector_db_client

    @log_execution_time
    def answer_question(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Executes the full RAG loop: Embed -> Search -> Prompt -> Generate.

        Args:
            query: The user's raw question string.
            top_k: The number of relevant context passages to retrieve.

        Returns:
            A dictionary containing the AI's textual answer and the cited sources.
        """
        logger.info(f"Processing RAG query: '{query}'")

        # Step 1: Convert the text query into a math vector
        query_vector = self.embedding_manager.get_query_embedding(query)

        # Step 2: Retrieve relevant documents from the vector database
        # (Using a placeholder method here until the DB client is wired up)
        context_chunks = self._execute_vector_search(query_vector, top_k)

        # Step 3: Handle empty context gracefully using our pre-registered prompt
        if not context_chunks:
            logger.warning("No relevant context found in the database for the query.")
            fallback_message = render_prompt(PromptName.RAG_NO_CONTEXT_FALLBACK, query=query)
            return {
                "answer": fallback_message,
                "sources": []
            }

        # Step 4: Format the retrieved context into a single string block
        formatted_context = "\n\n".join(
            [f"[Passage {i+1}]:\n{chunk['text']}" for i, chunk in enumerate(context_chunks)]
        )

        # Step 5: Render the final LLM prompt using the prompts registry
        system_prompt = render_prompt(
            PromptName.RAG_ANSWER_SYSTEM,
            context_passages=formatted_context,
            query=query
        )

        # Step 6: Generate the final answer using the LLM client
        logger.debug("Dispatching populated context to the LLM for generation...")
        answer = self.llm_client.generate(prompt=system_prompt)

        logger.info("Successfully generated grounded RAG response.")
        
        # Extract metadata from the chunks to use as citations
        sources = [chunk.get("metadata", {}) for chunk in context_chunks]

        return {
            "answer": answer,
            "sources": sources
        }

    def _execute_vector_search(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Placeholder for the actual vector database retrieval logic.
        
        Your full-stack engineer will replace this logic with actual calls to 
        your specific vector DB (e.g., `self.vector_db.search(vector, limit=top_k)`).
        """
        # Mock data structure representing what a Vector DB should return
        return [
            {
                "text": "KMRL safety guidelines mandate daily track inspections.", 
                "metadata": {"page": 12, "document": "safety_manual.pdf"}
            },
            {
                "text": "Budget approvals for Q3 were finalized in the October board meeting.", 
                "metadata": {"page": 3, "document": "financials_Q3.pdf"}
            }
        ][:top_k]