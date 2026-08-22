"""Generic, stateless text/string primitives for the KMRL platform.

Scope is deliberately narrow: whitespace collapsing, safe truncation,
naive sentence splitting, and basic similarity helpers. Document-specific
cleaning pipelines (header/footer stripping, OCR artifact repair) belong
in `preprocessing/cleaner.py`; locale-aware normalization belongs in
`preprocessing/text_normalizer.py`. Both build on top of this module.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

_WHITESPACE_PATTERN = re.compile(r"\s+")
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def collapse_whitespace(text: str) -> str:
    """Collapses all runs of whitespace (including newlines/tabs) into single spaces.

    Args:
        text: The input text, potentially containing irregular spacing
            from OCR output or PDF extraction (multiple spaces, tabs,
            stray newlines mid-sentence).

    Returns:
        The text with all whitespace runs replaced by a single space,
        and leading/trailing whitespace stripped.

    Example:
        >>> collapse_whitespace("Hello   \\n\\n  world\\t!")
        'Hello world !'
    """
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    """Normalizes Unicode text to a consistent canonical form.

    Important for text extracted via OCR or from PDFs/DOCX, which can
    contain visually identical but differently-encoded characters (e.g.
    full-width vs. half-width digits, combining vs. precomposed accents),
    which would otherwise break exact-match operations like deduplication
    or keyword search.

    Args:
        text: The input text to normalize.
        form: One of "NFC", "NFKC", "NFD", "NFKD" (standard `unicodedata`
            normalization forms). "NFKC" is the recommended default for
            search/matching use cases.

    Returns:
        The Unicode-normalized text.

    Raises:
        ValueError: If `form` is not one of the four valid forms.
    """
    valid_forms = {"NFC", "NFKC", "NFD", "NFKD"}
    if form not in valid_forms:
        raise ValueError(f"form must be one of {valid_forms}, got {form!r}")
    return unicodedata.normalize(form, text)


def truncate_text(text: str, max_characters: int, ellipsis: str = "...") -> str:
    """Truncates text to a maximum character length, appending an ellipsis.

    Truncation happens at the nearest preceding word boundary (rather
    than mid-word) when possible, so truncated output remains readable.

    Args:
        text: The text to truncate.
        max_characters: The maximum length of the returned string,
            including the ellipsis.
        ellipsis: The suffix appended to indicate truncation.

    Returns:
        The original text if it already fits within `max_characters`,
        otherwise a truncated version ending in `ellipsis`.

    Raises:
        ValueError: If `max_characters` is smaller than `len(ellipsis)`.
    """
    if max_characters < len(ellipsis):
        raise ValueError(
            f"max_characters ({max_characters}) must be >= len(ellipsis) ({len(ellipsis)})"
        )
    if len(text) <= max_characters:
        return text

    budget = max_characters - len(ellipsis)
    truncated = text[:budget]
    last_space_index = truncated.rfind(" ")
    if last_space_index > 0:
        truncated = truncated[:last_space_index]
    return truncated.rstrip() + ellipsis


def count_words(text: str) -> int:
    """Counts whitespace-delimited words in a text string.

    Args:
        text: The input text.

    Returns:
        The number of whitespace-delimited tokens. Not a substitute for a
        proper LLM tokenizer count -- use `embeddings/embedding_model.py`
        or the LLM client's tokenizer for token-accurate counts.
    """
    return len(text.split())


def split_into_sentences(text: str) -> List[str]:
    """Splits text into sentences using a lightweight punctuation heuristic.

    This is a naive, language-agnostic-ish splitter suitable for chunking
    heuristics and readability checks. It is NOT a substitute for a proper
    NLP sentence tokenizer (e.g. spaCy) when linguistic accuracy matters;
    `preprocessing/chunker.py` may swap in a model-based splitter later
    while keeping this as a fast fallback.

    Args:
        text: The input text, ideally already whitespace-collapsed via
            `collapse_whitespace`.

    Returns:
        A list of sentence strings, with surrounding whitespace stripped.
        Empty strings are filtered out.

    Example:
        >>> split_into_sentences("Hello world. This is KMRL. Is it working?")
        ['Hello world.', 'This is KMRL.', 'Is it working?']
    """
    if not text.strip():
        return []
    raw_sentences = _SENTENCE_BOUNDARY_PATTERN.split(text.strip())
    return [sentence.strip() for sentence in raw_sentences if sentence.strip()]


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Computes word-level Jaccard similarity between two texts.

    A fast, embedding-free similarity heuristic useful for cheap
    pre-filtering (e.g. skipping obviously distinct texts before running
    a more expensive cosine-similarity check in
    `retrieval/duplicate_detector.py`).

    Args:
        text_a: The first text.
        text_b: The second text.

    Returns:
        A float in [0.0, 1.0]: the size of the word-set intersection
        divided by the size of the word-set union. Returns 0.0 if both
        texts are empty.
    """
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a and not words_b:
        return 0.0

    intersection_size = len(words_a & words_b)
    union_size = len(words_a | words_b)
    return intersection_size / union_size if union_size else 0.0


def is_mostly_non_alphabetic(text: str, threshold: float = 0.5) -> bool:
    """Detects text that is likely OCR garbage (mostly symbols/digits, not letters).

    Useful as a quick quality gate on OCR output before it enters the
    preprocessing pipeline, flagging pages that likely failed OCR.

    Args:
        text: The text to inspect.
        threshold: The fraction of non-alphabetic characters (of all
            non-whitespace characters) above which the text is
            considered "mostly non-alphabetic".

    Returns:
        True if the fraction of non-alphabetic, non-whitespace characters
        meets or exceeds `threshold`. Returns False for empty text.
    """
    non_whitespace_chars = [char for char in text if not char.isspace()]
    if not non_whitespace_chars:
        return False

    non_alphabetic_count = sum(1 for char in non_whitespace_chars if not char.isalpha())
    return (non_alphabetic_count / len(non_whitespace_chars)) >= threshold