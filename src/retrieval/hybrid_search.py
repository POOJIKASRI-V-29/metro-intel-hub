"""Hybrid search engine for the KMRL Platform.

Fuses the results of a lexical engine (BM25) and a dense/semantic engine using
Reciprocal Rank Fusion (RRF). RRF is robust because it combines *rankings* rather than
raw scores, so the two engines' incomparable score scales do not need normalization.
Implements the :class:`BaseSearchEngine` contract.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging import get_logger
from . import BaseSearchEngine, RetrievalHit
from ..preprocessing.chunker import TextChunk

logger = get_logger(__name__)


class HybridSearchEngine(BaseSearchEngine):
    """Combines a lexical and a dense engine via Reciprocal Rank Fusion."""

    def __init__(
        self,
        lexical_engine: BaseSearchEngine,
        dense_engine: BaseSearchEngine,
        rrf_k: int = 60,
    ) -> None:
        """
        Args:
            lexical_engine: A keyword engine (e.g. :class:`BM25SearchEngine`).
            dense_engine: A vector/semantic engine implementing ``BaseSearchEngine``.
            rrf_k: RRF dampening constant; larger values reduce the weight of top ranks.
        """
        self.lexical_engine = lexical_engine
        self.dense_engine = dense_engine
        self.rrf_k = rrf_k

    def build_index(self, chunks: List[TextChunk]) -> None:
        """Build the index on both underlying engines."""
        self.lexical_engine.build_index(chunks)
        self.dense_engine.build_index(chunks)
        logger.info("Hybrid index built on lexical + dense engines (%d chunks).", len(chunks))

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalHit]:
        """Fuse lexical and dense rankings for ``query`` and return the top ``top_k``."""
        # Fetch a deeper candidate pool from each engine so fusion has material to work with.
        pool = max(top_k * 4, 20)
        lexical_hits = self.lexical_engine.search(query, top_k=pool, filters=filters)
        dense_hits = self.dense_engine.search(query, top_k=pool, filters=filters)

        fused: Dict[str, Dict[str, Any]] = {}

        def _fuse(hits: List[RetrievalHit], source: str) -> None:
            for rank, hit in enumerate(hits, start=1):
                cid = hit.chunk.chunk_id
                entry = fused.setdefault(cid, {"chunk": hit.chunk, "score": 0.0, "sources": []})
                entry["score"] += 1.0 / (self.rrf_k + rank)
                entry["sources"].append(source)

        _fuse(lexical_hits, "bm25")
        _fuse(dense_hits, "vector")

        ranked = sorted(fused.values(), key=lambda e: e["score"], reverse=True)

        return [
            RetrievalHit(
                chunk=entry["chunk"],
                score=float(entry["score"]),
                retrieval_type="hybrid",
                metadata_overlay={"fused_from": entry["sources"]},
            )
            for entry in ranked[:top_k]
        ]
