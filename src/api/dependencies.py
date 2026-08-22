"""FastAPI dependency providers for the KMRL Document Intelligence API.

This module centralizes construction of the platform's heavy singletons (embedding
model, vector store, LLM manager) and the request pipelines that compose them.

Design notes
------------
* **Lazy**: heavy modules (torch / sentence-transformers / qdrant-client / openai) are
  imported *inside* the provider functions, never at module import time. This keeps the
  FastAPI app importable and bootable without the full ML stack installed.
* **Cached**: successfully-built singletons are memoized for the process lifetime.
* **Graceful**: if a backend cannot be constructed (missing dependency or unreachable
  service), the request-scoped providers raise HTTP 503 rather than a raw 500, so the
  API degrades cleanly instead of crashing.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict

from fastapi import HTTPException, status

logger = logging.getLogger("document_intelligence.api.dependencies")

# Process-wide singleton registry.
_SINGLETONS: Dict[str, Any] = {}


def _service_unavailable(name: str, error: Exception) -> HTTPException:
    logger.error("Dependency '%s' is unavailable: %s", name, error, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"The '{name}' backend is not available. Ensure its dependencies are "
            f"installed and any required service (e.g. Qdrant, Ollama) is running."
        ),
    )


def _get_or_build(key: str, builder: Callable[[], Any]) -> Any:
    """Return the cached singleton for ``key``, building it on first use.

    Any exception raised by ``builder`` is translated into an HTTP 503 so route
    handlers surface a clean "service unavailable" instead of an opaque 500.
    """
    if key not in _SINGLETONS:
        try:
            _SINGLETONS[key] = builder()
        except HTTPException:
            raise
        except Exception as error:  # noqa: BLE001 - deliberately broad; surfaced as 503
            raise _service_unavailable(key, error) from error
    return _SINGLETONS[key]


# --------------------------------------------------------------------------- #
# Core singletons
# --------------------------------------------------------------------------- #

def get_embedding_manager():
    """Return the shared embedding model manager (loads the bi-encoder on first use)."""
    def build():
        from src.embeddings.manager import EmbeddingManager
        return EmbeddingManager()

    return _get_or_build("embedding_manager", build)


def get_vector_store():
    """Return the shared vector-store client (Qdrant by default)."""
    def build():
        from src.vector_store.qdrant_provider import QdrantProvider
        return QdrantProvider(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            api_key=os.getenv("QDRANT_API_KEY") or None,
        )

    return _get_or_build("vector_store", build)


def get_llm_manager():
    """Return the shared LLM answer-generation manager."""
    def build():
        from src.generation.llm_manager import LLMManager
        return LLMManager()

    return _get_or_build("llm_manager", build)


# --------------------------------------------------------------------------- #
# Composed pipelines
# --------------------------------------------------------------------------- #

def get_retrieval_pipeline():
    """Return the shared stateless retrieval pipeline."""
    def build():
        from src.pipeline.retrieval_pipeline import RetrievalPipeline
        return RetrievalPipeline(
            embedder=get_embedding_manager(),
            vector_store=get_vector_store(),
        )

    return _get_or_build("retrieval_pipeline", build)


def get_upload_pipeline():
    """Return the shared document ingestion pipeline."""
    def build():
        from src.ingestion.document_loader import DocumentLoader
        from src.preprocessing.cleaner import TextCleaner
        from src.preprocessing.chunker import TokenAwareChunker
        from src.pipeline.upload_pipeline import DocumentUploadPipeline

        return DocumentUploadPipeline(
            loader=DocumentLoader(),
            cleaner=TextCleaner(),
            chunker=TokenAwareChunker(),
            embedder=get_embedding_manager(),
            vector_store=get_vector_store(),
        )

    return _get_or_build("upload_pipeline", build)


def get_search_pipeline():
    """Return the shared document search pipeline."""
    def build():
        from src.pipeline.search_pipeline import SearchPipeline
        return SearchPipeline(retrieval_pipeline=get_retrieval_pipeline())

    return _get_or_build("search_pipeline", build)


def get_chat_pipeline():
    """Return the shared conversational RAG pipeline."""
    def build():
        from src.pipeline.chat_pipeline import ChatPipeline
        return ChatPipeline(
            retrieval_pipeline=get_retrieval_pipeline(),
            llm_manager=get_llm_manager(),
        )

    return _get_or_build("chat_pipeline", build)


def reset_singletons() -> None:
    """Clear the singleton cache (useful for tests)."""
    _SINGLETONS.clear()
