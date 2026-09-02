"""
Embedding data contracts for the KMRL Platform.

This module holds only the lightweight pydantic schemas describing how embeddings are
configured and carried through the pipeline. It deliberately imports neither torch nor
sentence-transformers, so it stays importable in contexts without the ML stack; the
model-execution logic lives in ``src.embeddings.manager``.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from config.settings import get_settings

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.embeddings.embedding_schema")


class EmbeddingConfig(BaseModel):
    """
    Configuration properties controlling embedding model deployments.

    Defaults are resolved from ``config.settings`` (the ``EMBEDDING_`` env prefix) so the
    runtime model, device and batching stay in one place instead of drifting between the
    settings module and hard-coded literals here.
    """
    model_name: str = Field(
        default_factory=lambda: get_settings().embedding.model_name,
        description="HuggingFace model string repo identifier."
    )
    batch_size: int = Field(
        default_factory=lambda: get_settings().embedding.batch_size,
        description="Number of text items to process simultaneously in a single forward pass."
    )
    normalize_embeddings: bool = Field(
        default_factory=lambda: get_settings().embedding.normalize_embeddings,
        description="Enforce unit-length scale mapping to simplify similarity calculation."
    )
    device: Optional[str] = Field(
        default_factory=lambda: get_settings().embedding.device or None,
        description="Explicit device override ('cuda', 'mps', 'cpu'). Auto-detected if None."
    )

    model_config = ConfigDict(frozen=True, protected_namespaces=())


class VectorizedChunk(BaseModel):
    """
    The data envelope combining a TextChunk with its corresponding dense numerical embedding vector.
    """
    chunk_id: str = Field(..., description="Unique matching identifier originating from the TextChunk phase.")
    text: str = Field(..., description="The raw textual fragment source.")
    embedding: List[float] = Field(..., description="Dense multi-dimensional floating-point numerical vector representation.")
    chunk_index: int = Field(..., description="Sequence order rank inside the root parent document.")
