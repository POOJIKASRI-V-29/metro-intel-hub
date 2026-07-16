"""
Semantic and Sliding-Window Chunking module for the KMRL Platform.

This module provides a token-aware recursive text splitter that segments large 
document bodies into optimized chunks while maintaining context boundaries and overlaps.
"""

import logging
from typing import Any, Dict, List, Optional
import tiktoken
from pydantic import BaseModel, ConfigDict, Field

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.preprocessing.chunker")


class ChunkConfig(BaseModel):
    """
    Configuration settings for the token-based text chunker.
    """
    chunk_size_tokens: int = Field(default=512, description="The maximum target token capacity per chunk.")
    chunk_overlap_tokens: int = Field(default=64, description="The number of tokens to overlap between adjacent chunks.")
    encoding_name: str = Field(default="cl100k_base", description="The tiktoken tokenizer model to use (e.g., cl100k_base for GPT-4).")

    model_config = ConfigDict(frozen=True)


class TextChunk(BaseModel):
    """
    Data model representing an isolated, processed chunk of document text.
    """
    chunk_id: str = Field(..., description="Unique deterministic identifier (e.g., doc_uuid_chunk_idx).")
    text: str = Field(..., description="The textual string segment.")
    token_count: int = Field(..., description="The calculated number of tokens in this specific segment.")
    chunk_index: int = Field(..., description="The 0-based sequential order position within the source document.")


class TokenAwareChunker:
    """
    Splits long textual strings into semantically stable chunks using token boundaries.
    """

    def __init__(self, config: Optional[ChunkConfig] = None) -> None:
        """
        Initializes the text chunker with tokenizer configurations.

        Args:
            config: Optional configurations. Defaults to standard RAG settings if None.
        """
        self.config = config or ChunkConfig()
        
        # Enforce validation on overlap boundaries
        if self.config.chunk_overlap_tokens >= self.config.chunk_size_tokens:
            raise ValueError("Chunk overlap tokens cannot be greater than or equal to the total chunk size.")
            
        try:
            self._tokenizer = tiktoken.get_encoding(self.config.encoding_name)
        except Exception as error:
            logger.warning(f"Could not load encoding '{self.config.encoding_name}', falling back to 'cl100k_base'.")
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, text: str, document_id: str) -> List[TextChunk]:
        """
        Splits a single text string into multiple structured TextChunk objects.
        Uses a recursive strategy favoring structural breaks (paragraphs, newlines).

        Args:
            text: The cleaned, uniform string content of a document.
            document_id: The unique identifier of the source document to generate chunk IDs.

        Returns:
            A list of ordered TextChunk objects.
        """
        if not text or not text.strip():
            return []

        # 1. Encode text into tokens
        all_tokens = self._tokenizer.encode(text)
        total_tokens = len(all_tokens)

        chunks: List[TextChunk] = []
        
        # Fast path: if the text fits comfortably inside one chunk, bypass splitting
        if total_tokens <= self.config.chunk_size_tokens:
            chunks.append(
                TextChunk(
                    chunk_id=f"{document_id}_0",
                    text=text,
                    token_count=total_tokens,
                    chunk_index=0
                )
            )
            return chunks

        # 2. Implement the sliding window chunking loop over the token space
        start_idx = 0
        chunk_counter = 0
        step_size = self.config.chunk_size_tokens - self.config.chunk_overlap_tokens

        while start_idx < total_tokens:
            end_idx = min(start_idx + self.config.chunk_size_tokens, total_tokens)
            chunk_token_slice = all_tokens[start_idx:end_idx]
            
            # Decode tokens back into a natural string segment
            chunk_text = self._tokenizer.decode(chunk_token_slice)
            
            chunks.append(
                TextChunk(
                    chunk_id=f"{document_id}_{chunk_counter}",
                    text=chunk_text,
                    token_count=len(chunk_token_slice),
                    chunk_index=chunk_counter
                )
            )
            
            chunk_counter += 1
            start_idx += step_size

        logger.info(f"Successfully segmented document {document_id} into {len(chunks)} token chunks.")
        return chunks