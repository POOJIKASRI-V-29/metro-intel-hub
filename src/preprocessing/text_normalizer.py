"""Text normalization utilities for the KMRL Platform.

Complements ``TextCleaner`` (which strips noise) by *canonicalizing* text: Unicode
normalization, smart-quote/dash folding, optional accent stripping and case folding, and
whitespace collapsing. Normalizing before chunking and embedding improves lexical match
consistency (BM25) and reduces spurious duplicates. Dependency-free (stdlib only).
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, Field

from config.logging import get_logger

logger = get_logger(__name__)

# Map common "smart" punctuation to ASCII equivalents.
_PUNCT_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "―": "-",
    "…": "...", " ": " ",
}
_PUNCT_RE = re.compile("|".join(re.escape(k) for k in _PUNCT_MAP))
_WS_RE = re.compile(r"\s+")


class NormalizerConfig(BaseModel):
    """Toggles controlling the normalization passes."""
    form: str = Field(default="NFKC", description="Unicode normalization form (NFC/NFKC/NFD/NFKD).")
    fold_punctuation: bool = Field(default=True, description="Fold smart quotes/dashes/ellipses to ASCII.")
    strip_accents: bool = Field(default=False, description="Remove diacritics (é -> e).")
    lowercase: bool = Field(default=False, description="Lower-case the output.")
    collapse_whitespace: bool = Field(default=True, description="Collapse runs of whitespace to a single space.")


class TextNormalizer:
    """Applies a configurable, deterministic normalization pipeline to text."""

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        self.config = config or NormalizerConfig()

    def normalize(self, text: str) -> str:
        """Return a canonicalized version of ``text`` per the configured passes."""
        if not text:
            return ""

        result = unicodedata.normalize(self.config.form, text)

        if self.config.fold_punctuation:
            result = _PUNCT_RE.sub(lambda m: _PUNCT_MAP[m.group(0)], result)

        if self.config.strip_accents:
            decomposed = unicodedata.normalize("NFKD", result)
            result = "".join(ch for ch in decomposed if not unicodedata.combining(ch))

        if self.config.lowercase:
            result = result.lower()

        if self.config.collapse_whitespace:
            result = _WS_RE.sub(" ", result).strip()

        return result

    def normalize_batch(self, texts: list[str]) -> list[str]:
        """Normalize a list of strings."""
        return [self.normalize(t) for t in texts]
