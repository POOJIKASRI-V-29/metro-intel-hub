"""Near-duplicate detection for the KMRL Platform ingestion stage.

Detects both exact and near-duplicate text using two cheap, dependency-free signals:

* an exact content hash (SHA-256 of normalized text), and
* Jaccard similarity over word *shingles* (n-grams) for near-duplicates.

This runs before embedding so the corpus does not accumulate redundant vectors (e.g. the
"27 near-duplicate engineering drawings" the dashboard reports).
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional, Set

from pydantic import BaseModel, Field

from config.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class DuplicateMatch(BaseModel):
    """Describes why a piece of text was flagged as a duplicate."""
    is_duplicate: bool = Field(..., description="True if an exact or near duplicate was found.")
    match_id: Optional[str] = Field(default=None, description="Identifier of the matched existing item.")
    similarity: float = Field(default=0.0, description="Jaccard similarity to the closest match (0..1).")
    reason: str = Field(default="", description="'exact' or 'near' or '' when unique.")


def _shingles(text: str, n: int = 5) -> Set[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DuplicateDetector:
    """Stateful detector that remembers previously-seen documents in-process."""

    def __init__(self, threshold: float = 0.85, shingle_size: int = 5) -> None:
        """
        Args:
            threshold: Jaccard similarity at/above which two texts are "near duplicates".
            shingle_size: Word n-gram size used to build shingle sets.
        """
        self.threshold = threshold
        self.shingle_size = shingle_size
        self._hashes: dict[str, str] = {}  # content_hash -> item_id
        self._shingles: dict[str, Set[str]] = {}  # item_id -> shingle set

    @staticmethod
    def jaccard(a: Set[str], b: Set[str]) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    def check(self, text: str) -> DuplicateMatch:
        """Check ``text`` against everything registered so far (without registering it)."""
        if not text or not text.strip():
            return DuplicateMatch(is_duplicate=False)

        h = _content_hash(text)
        if h in self._hashes:
            return DuplicateMatch(
                is_duplicate=True, match_id=self._hashes[h], similarity=1.0, reason="exact"
            )

        sh = _shingles(text, self.shingle_size)
        best_id, best_sim = None, 0.0
        for item_id, existing in self._shingles.items():
            sim = self.jaccard(sh, existing)
            if sim > best_sim:
                best_id, best_sim = item_id, sim

        if best_sim >= self.threshold:
            return DuplicateMatch(
                is_duplicate=True, match_id=best_id, similarity=best_sim, reason="near"
            )
        return DuplicateMatch(is_duplicate=False, similarity=best_sim)

    def register(self, item_id: str, text: str) -> None:
        """Add ``text`` to the seen set under ``item_id``."""
        if not text or not text.strip():
            return
        self._hashes[_content_hash(text)] = item_id
        self._shingles[item_id] = _shingles(text, self.shingle_size)

    def add_if_unique(self, item_id: str, text: str) -> DuplicateMatch:
        """Check ``text``; register it only if it is unique. Returns the check result."""
        result = self.check(text)
        if not result.is_duplicate:
            self.register(item_id, text)
        return result

    def find_duplicates(self, texts: List[str]) -> List[DuplicateMatch]:
        """Batch helper: scan a list, returning the match verdict for each item in order."""
        self._hashes.clear()
        self._shingles.clear()
        results: List[DuplicateMatch] = []
        for idx, text in enumerate(texts):
            results.append(self.add_if_unique(f"item_{idx}", text))
        return results
