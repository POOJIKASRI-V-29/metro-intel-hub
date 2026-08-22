"""
Initialization entry point for the embeddings processing package.

Only the lightweight pydantic schemas are re-exported here. ``EmbeddingManager`` is
intentionally NOT imported at package level because it pulls in torch /
sentence-transformers; import it directly from ``src.embeddings.manager`` where needed.
"""

from .embedding_schema import EmbeddingConfig, VectorizedChunk

__all__ = [
    "EmbeddingConfig",
    "VectorizedChunk",
]
