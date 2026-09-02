"""
Abstract Base Interface and Schemas for the Vector Storage Sector.

This module enforces strict polymorphic contracts for all concrete Vector Database 
providers (e.g., Qdrant, Milvus, pgvector) using Python's Abstract Base Classes (ABC).
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..embeddings.embedding_schema import VectorizedChunk

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.vector_store.base")


class SearchFilter(BaseModel):
    """
    Data envelope defining metadata filter key-value constraints for vector lookups.
    Example: To search only within a specific file: SearchFilter(key="document_id", value="123-456")
    """
    key: str = Field(..., description="The metadata payload field name to apply the filtering rule against.")
    value: Any = Field(
        ...,
        description=(
            "The target value to match during lookup constraints: a scalar for an exact "
            "match, or a list/tuple/set for an any-of match across several values."
        ),
    )


class SearchResult(BaseModel):
    """
    Data representation of a prioritized matching block returned from the Vector DB.
    """
    chunk_id: str = Field(..., description="Unique matching identifier originating from the ingestion block phase.")
    text: str = Field(..., description="The raw textual source fragment stored inside the matching node.")
    score: float = Field(..., description="The calculated cosine-similarity or distance metric score (higher is better).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Associated storage metadata parameters.")


class BaseVectorStore(ABC):
    """
    Abstract Base Class outlining standard database operations for the KMRL Platform.
    All integration clients must inherit from this interface to preserve decoupling invariants.
    """

    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str = "Cosine") -> bool:
        """
        Creates and provisions a new isolated storage collection/index inside the Vector DB.

        Args:
            collection_name: Unique targeted partition index identifier string.
            vector_size: Dimensional capacity matching the embedding model outputs (e.g., 1024).
            distance_metric: Space comparison rule configuration (e.g., 'Cosine', 'Euclidean', 'Dot').

        Returns:
            True if operation succeeds, False otherwise.
        """
        pass

    @abstractmethod
    def upsert_chunks(self, collection_name: str, vectorized_chunks: List[VectorizedChunk], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inserts or updates vector matrix items along with their structural payload metadata records.

        Args:
            collection_name: Target partition index destination identifier.
            vectorized_chunks: Array list collection of dense float arrays and raw source strings.
            metadata: Global top-level operational tags to associate with these records (e.g., document_id, upload_timestamp).

        Returns:
            True if all points are acknowledged and stored, False otherwise.
        """
        pass

    @abstractmethod
    def search_similarity(
        self, 
        collection_name: str, 
        query_vector: List[float], 
        top_k: int = 5, 
        filters: Optional[List[SearchFilter]] = None
    ) -> List[SearchResult]:
        """
        Performs high-performance Approximate Nearest Neighbor (ANN) index matching.

        Args:
            collection_name: Target partition index to search against.
            query_vector: Dense floating-point array mapping representing the target user query string.
            top_k: Total max quantity limit of prioritization hits to return.
            filters: Optional search filters to prune candidate search points prior to vector space evaluations.

        Returns:
            An ordered, prioritized list of SearchResult matches.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """
        Purges an index collection and wipes all underlying data blocks permanently.

        Args:
            collection_name: Targeted database partition identifier to drop.

        Returns:
            True if deleted successfully, False otherwise.
        """
        pass