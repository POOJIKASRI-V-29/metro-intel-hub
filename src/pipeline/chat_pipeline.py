"""
Conversational RAG Pipeline for the KMRL Platform.

This module orchestrates multi-turn interactions, maintaining conversation 
history and injecting it alongside vector-retrieved context to allow 
users to ask contextual follow-up questions.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import downstream pipelines and managers
from .retrieval_pipeline import RetrievalPipeline
from ..generation.llm_manager import LLMManager, GeneratedAnswer
from ..vector_store.base import SearchResult

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.chat_pipeline")


class ChatMessage(BaseModel):
    """
    Standardized schema for a single conversational turn.
    """
    role: str = Field(..., description="The author of the message: 'user' or 'assistant'.")
    content: str = Field(..., description="The textual content of the message.")


class ChatPipeline:
    """
    Master pipeline orchestrating memory-augmented RAG conversations.
    """

    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline,
        llm_manager: LLMManager,
        max_history_turns: int = 5
    ) -> None:
        """
        Initializes the chat pipeline with its required sub-pipelines.

        Args:
            retrieval_pipeline: Configured instance of the stateless retrieval pipeline.
            llm_manager: Configured instance of the generation engine.
            max_history_turns: The maximum number of previous messages to inject (prevents token overflow).
        """
        self.retrieval_pipeline = retrieval_pipeline
        self.llm_manager = llm_manager
        self.max_history_turns = max_history_turns

    def _format_history_for_prompt(self, history: List[ChatMessage]) -> str:
        """
        Translates structural chat messages into a readable string block for the LLM.
        """
        if not history:
            return "No previous conversation history."

        # Truncate to the most recent N turns to protect the context window
        recent_history = history[-(self.max_history_turns * 2):]
        
        formatted_lines = []
        for msg in recent_history:
            role_label = "User" if msg.role == "user" else "Assistant"
            formatted_lines.append(f"{role_label}: {msg.content}")

        return "\n".join(formatted_lines)

    def execute_chat_turn(
        self, 
        current_query: str, 
        chat_history: List[ChatMessage], 
        filters: Optional[Dict[str, Any]] = None
    ) -> GeneratedAnswer:
        """
        Executes a single conversational turn, fetching context and synthesizing a response.

        Args:
            current_query: The immediate question the user just typed.
            chat_history: Ordered list of previous interactions in this session.
            filters: Optional metadata constraints to restrict the document search.

        Returns:
            A GeneratedAnswer object containing the LLM's response.
        """
        logger.info(f"--- Starting chat turn for query: '{current_query}' ---")

        try:
            # Step 1: Retrieve context based on the current query
            logger.debug("Retrieving relevant document chunks...")
            context_chunks: List[SearchResult] = self.retrieval_pipeline.retrieve_context(
                query=current_query,
                top_k=5,
                filters=filters
            )

            # Step 2: Format the conversation memory
            logger.debug(f"Formatting {len(chat_history)} previous messages for memory injection...")
            history_text = self._format_history_for_prompt(chat_history)

            # Step 3: Augment the current query with the formatted history
            # We wrap this so the underlying LLMManager doesn't need to change its signature
            augmented_query = (
                f"Previous Conversation History:\n"
                f"{history_text}\n\n"
                f"Current User Question:\n"
                f"{current_query}\n\n"
                f"Please answer the Current User Question based on the context provided. "
                f"Use the Previous Conversation History only if it helps clarify what the user is asking."
            )

            # Step 4: Generate the final answer using the LLMManager
            logger.debug("Passing augmented prompt and context to the LLM generation engine...")
            final_answer = self.llm_manager.generate_answer(
                query=augmented_query,
                context_chunks=context_chunks
            )

            logger.info("--- Chat turn completed successfully. ---")
            return final_answer

        except Exception as error:
            logger.exception("The chat pipeline encountered a fatal execution failure.")
            raise RuntimeError(f"Failed to execute chat turn: {str(error)}") from error