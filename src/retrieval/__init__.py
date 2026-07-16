"""
Base Retrieval Interface Definitions for the KMRL Platform.

This module establishes the unified contracts, structural types, and abstract 
classes that all downstream search mechanisms (BM25, Dense Vector, Hybrid) 
must implement to ensure seamless compatibility across orchestration layers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ..preprocessing.chunker import TextChunk


class RetrievalHit(BaseModel):
    """
    Standardized wrapper for a single document chunk retrieved from any search backend.
    
    Normalizes the variance between different engines (e.g., Qdrant scores vs. BM25 scores).
    """
    chunk: TextChunk = Field(..., description="The physical text snippet entity and its origin structural context.")
    score: float = Field(..., description="The structural match confidence or distance metric assigned by the backend.")
    retrieval_type: str = Field(..., description="Identifies the source layer (e.g., 'vector', 'bm25', 'hybrid').")
    metadata_overlay: Dict[str, Any] = Field(default_factory=dict, description="Engine-specific execution data.")


class BaseSearchEngine(ABC):
    """
    Abstract Base Class acting as the strict protocol blueprint for all platform retrieval engines.
    """

    @abstractmethod
    def build_index(self, chunks: List[TextChunk]) -> None:
        """
        Populates or initializes the engine's tracking registry with underlying text blocks.
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[RetrievalHit]:
        """
        Executes an isolated query transaction against the indexed domain.

        Args:
            query: The processed natural language string or raw keyword phrase.
            top_k: Limit boundaries determining total matching results returned.
            filters: Optional dictionary schema to apply strict metadata scoping.

        Returns:
            A sorted collection of generalized RetrievalHit data envelopes.
        """
        pass