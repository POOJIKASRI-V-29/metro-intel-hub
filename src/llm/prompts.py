"""
Centralized Prompt Template Registry for the KMRL Generation Layer.

This module houses all system instructions, context formatting wrappers, and 
task blueprints, keeping string manipulation separate from runtime client logic.
"""

from typing import Dict, Any, List


class PromptRegistry:
    """
    Static repository containing foundational instructions and formatting wrappers for LLM operations.
    """

    # --- System Instructions ---
    
    SYSTEM_CORE_ASSISTANT = (
        "You are an expert, highly precise enterprise knowledge assistant. "
        "Your goal is to provide clear, actionable, and strictly factual answers based "
        "exclusively on the verified document context provided to you. "
        "Maintain a neutral, professional tone at all times."
    )

    SYSTEM_STRICT_RAG = (
        "You are a strict technical document question-answering system.\n"
        "Analyze the provided source text snippets carefully before formulating your response.\n"
        "CRITICAL RULES:\n"
        "1. Base your answer ONLY on the provided document snippets. Do not assume or extrapolate.\n"
        "2. If the answer cannot be confidently derived from the context, respond exactly with: "
        "'I am sorry, but the provided documentation does not contain sufficient information to answer this query.'\n"
        "3. Do not leverage external training data or pre-existing world knowledge to invent facts."
    )

    SYSTEM_QUERY_REWRITER = (
        "You are an expert linguistics pre-processor. Your task is to analyze a conversation history "
        "and a follow-up question, and compress them into a single standalone search query. "
        "This query will be used to look up vector embeddings in a database. "
        "Do not answer the question; only return the optimized, standalone query string."
    )

    # --- User-Facing Templates ---

    RAG_CONTEXT_TEMPLATE = (
        "CONTEXT SNIPPETS:\n"
        "--------------------------------------------------\n"
        "{context_text}\n"
        "--------------------------------------------------\n\n"
        "USER QUESTION: {user_query}\n\n"
        "FINAL ANSWER:"
    )

    CONVERSATIONAL_CONDENSE_TEMPLATE = (
        "CHAT HISTORY LOG:\n"
        "{chat_history}\n\n"
        "FOLLOW-UP USER TURN: {latest_query}\n\n"
        "Based on the conversation above, output a single search string optimized for vector database retrieval:"
    )

    @classmethod
    def format_rag_prompt(cls, context_chunks: List[Any], user_query: str) -> str:
        """
        Gathers extracted text segments and joins them into a single structured RAG context.

        Args:
            context_chunks: A list of objects containing a `.text` parameter.
            user_query: The literal question input string.

        Returns:
            A formatted prompt string ready for submission to the LLM client wrapper.
        """
        # Join chunks with explicit demarcation bounds to maintain structural readability
        joined_snippets = "\n\n".join(
            f"[Source Segment #{idx + 1}]:\n{chunk.text}"
            for idx, chunk in enumerate(context_chunks)
        )
        
        return cls.RAG_CONTEXT_TEMPLATE.format(
            context_text=joined_snippets,
            user_query=user_query
        )

    @classmethod
    def format_history_summary(cls, history_turns: List[Dict[str, str]], latest_query: str) -> str:
        """
        Formatively serializes a conversation log array into a text stream block.

        Args:
            history_turns: List of dictionaries matching the format: {'role': 'user'|'assistant', 'content': '...'}.
            latest_query: The new un-contextualized follow-up string.

        Returns:
            A structured history condensation prompt string.
        """
        serialized_history = ""
        for turn in history_turns:
            role_label = "User" if turn.get("role") == "user" else "Assistant"
            serialized_history += f"{role_label}: {turn.get('content', '')}\n"

        return cls.CONVERSATIONAL_CONDENSE_TEMPLATE.format(
            chat_history=serialized_history.strip(),
            latest_query=latest_query
        )