"""
Initialization entry point for the embeddings processing package.
"""

from .schemas import EmbeddingConfig, VectorizedChunk
from .manager import EmbeddingManager

__all__ = [
    "EmbeddingConfig",
    "VectorizedChunk",
    "EmbeddingManager",
]