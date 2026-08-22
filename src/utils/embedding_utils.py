"""Generic embedding and vector math utilities for the KMRL platform.

Scope: cosine similarity, L2 normalization, and payload batching for
external embedding APIs. Operations here are purely mathematical or
structural. External API calls to OpenAI or local embedding models 
belong in `llm/embedding_client.py`, not here.
"""

from __future__ import annotations

import math
from typing import Iterator, Sequence, TypeVar

from config.logging import get_logger

logger = get_logger(__name__)

# Type variable to allow batching generic lists (e.g., raw strings, Chunk objects)
T = TypeVar("T")


def compute_cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Computes the cosine similarity between two high-dimensional vectors.

    Calculates the normalized dot product to determine semantic similarity,
    where 1.0 implies exact directional alignment and -1.0 implies opposite.

    Args:
        vec_a: The first embedding vector sequence.
        vec_b: The second embedding vector sequence.

    Returns:
        A float representing the similarity score between -1.0 and 1.0. 
        Returns 0.0 if either vector has a magnitude of zero.

    Raises:
        ValueError: If the vectors have differing dimensions.

    Example:
        >>> compute_cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        1.0
        >>> compute_cosine_similarity([1.0, 0.0], [0.0, 1.0])
        0.0
    """
    dim_a = len(vec_a)
    dim_b = len(vec_b)
    
    if dim_a != dim_b:
        raise ValueError(f"Dimension mismatch: vec_a({dim_a}) vs vec_b({dim_b}).")

    if dim_a == 0:
        raise ValueError("Cannot compute similarity of empty vectors.")

    dot_product = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0

    for a, b in zip(vec_a, vec_b):
        dot_product += a * b
        norm_a_sq += a * a
        norm_b_sq += b * b

    if norm_a_sq == 0.0 or norm_b_sq == 0.0:
        logger.warning("Attempted to compute cosine similarity with a zero-magnitude vector.")
        return 0.0

    return dot_product / (math.sqrt(norm_a_sq) * math.sqrt(norm_b_sq))


def normalize_l2(vector: list[float]) -> list[float]:
    """Applies L2 normalization to an embedding vector.

    Scales the vector so that its Euclidean length (magnitude) equals 1.0.
    This is often required before storing vectors in databases like Qdrant 
    or Pinecone if you intend to use the dot-product metric as a proxy 
    for cosine similarity (which is computationally faster).

    Args:
        vector: A list of floats representing the raw embedding.

    Returns:
        A new list of floats representing the normalized vector.

    Raises:
        ValueError: If the vector is empty or has a magnitude of zero.
    """
    if not vector:
        raise ValueError("Cannot normalize an empty vector.")

    magnitude_sq = sum(x * x for x in vector)
    
    if magnitude_sq == 0.0:
        raise ValueError("Cannot normalize a zero-magnitude vector.")
        
    magnitude = math.sqrt(magnitude_sq)
    return [x / magnitude for x in vector]


def batch_iterable(items: Sequence[T], batch_size: int) -> Iterator[Sequence[T]]:
    """Yields successive n-sized batches from a sequence.

    Used primarily to chunk large lists of documents into smaller payloads 
    to respect external embedding API limits (e.g., OpenAI's max input array 
    size or payload byte limits).

    Args:
        items: The sequence of items (strings, dictionaries, objects) to batch.
        batch_size: The maximum number of items per batch.

    Yields:
        A sequence containing at most `batch_size` items.

    Raises:
        ValueError: If `batch_size` is less than 1.

    Example:
        >>> list(batch_iterable([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    if batch_size < 1:
        raise ValueError(f"Batch size must be >= 1, got {batch_size}")

    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]