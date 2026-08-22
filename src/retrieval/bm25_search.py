"""BM25 lexical search engine for the KMRL Platform.

A dependency-free implementation of the Okapi BM25 ranking function. It complements
the dense vector engine by matching exact terms (IDs, acronyms, part numbers) that
embedding models often blur together. Implements the :class:`BaseSearchEngine` contract
so it is interchangeable with the vector and hybrid engines.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from config.logging import get_logger
from . import BaseSearchEngine, RetrievalHit
from ..preprocessing.chunker import TextChunk

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25SearchEngine(BaseSearchEngine):
    """In-memory Okapi BM25 keyword search over indexed text chunks."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: List[TextChunk] = []
        self._doc_freqs: List[Counter] = []
        self._doc_len: List[int] = []
        self._avg_len: float = 0.0
        self._idf: Dict[str, float] = {}

    def build_index(self, chunks: List[TextChunk]) -> None:
        """Tokenize every chunk and precompute document frequencies and IDF weights."""
        self._chunks = list(chunks)
        doc_tokens = [_tokenize(c.text) for c in self._chunks]
        self._doc_freqs = [Counter(toks) for toks in doc_tokens]
        self._doc_len = [len(toks) for toks in doc_tokens]
        n = len(self._chunks)
        self._avg_len = (sum(self._doc_len) / n) if n else 0.0

        df: Counter = Counter()
        for freqs in self._doc_freqs:
            df.update(freqs.keys())

        # Okapi BM25 idf with the standard +0.5 smoothing (floored at a small positive).
        self._idf = {
            term: max(1e-6, math.log((n - freq + 0.5) / (freq + 0.5) + 1.0))
            for term, freq in df.items()
        }
        logger.info("BM25 index built over %d chunks (%d unique terms).", n, len(self._idf))

    def _score(self, query_tokens: List[str], doc_idx: int) -> float:
        freqs = self._doc_freqs[doc_idx]
        dl = self._doc_len[doc_idx]
        if dl == 0 or self._avg_len == 0:
            return 0.0
        score = 0.0
        for term in query_tokens:
            tf = freqs.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf.get(term, 0.0)
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self._avg_len)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalHit]:
        """Return the ``top_k`` chunks ranked by BM25 relevance to ``query``."""
        if not self._chunks:
            logger.warning("BM25 search called before build_index; returning no hits.")
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored = [
            (idx, self._score(query_tokens, idx)) for idx in range(len(self._chunks))
        ]
        scored = [pair for pair in scored if pair[1] > 0.0]
        scored.sort(key=lambda p: p[1], reverse=True)

        hits: List[RetrievalHit] = []
        for idx, score in scored[:top_k]:
            hits.append(
                RetrievalHit(
                    chunk=self._chunks[idx],
                    score=float(score),
                    retrieval_type="bm25",
                    metadata_overlay={"rank": len(hits) + 1},
                )
            )
        return hits
