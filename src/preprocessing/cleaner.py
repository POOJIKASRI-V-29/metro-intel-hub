"""
Text Preprocessing and Cleaning module for the KMRL Platform.

This module provides deterministic text normalization pipelines to scrub control characters,
resolve Unicode variances, collapse excessive whitespace, and minimize common OCR glitches.
"""

import logging
import re
import unicodedata
from pydantic import BaseModel, ConfigDict, Field

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.preprocessing.cleaner")


class CleanerConfig(BaseModel):
    """
    Configuration properties controlling text-cleaning strictness levels.
    """
    lowercase: bool = Field(default=False, description="Convert all text to lowercase strings.")
    strip_accents: bool = Field(default=False, description="Strip diacritics and accents from characters.")
    remove_extra_whitespace: bool = Field(default=True, description="Collapse multiple consecutive space characters.")
    normalize_unicode_form: str = Field(default="NFKC", description="Target Unicode normalization method (NFKC, NFKD, NFC, NFD).")

    model_config = ConfigDict(frozen=True)


class TextCleaner:
    """
    Executes sequential string cleaning operations to prepare text for chunking and tokenization.
    """

    def __init__(self, config: CleanerConfig | None = None) -> None:
        """
        Initializes the text cleaner with rule metrics.

        Args:
            config: Optional configurations. Defaults to baseline settings if None.
        """
        self.config = config or CleanerConfig()
        
        # Pre-compile regular expressions once during initialization to optimize high-volume iterations
        # Matches non-printable control characters (ASCII 0-31, 127-159)
        self._control_char_regex = re.compile(r"[\x00-\x1F\x7F-\x9F]")
        # Matches multiple consecutive white-space or tab layouts
        self._whitespace_regex = re.compile(r"[ \t]+")
        # Matches excessive vertical newline spaces to keep paragraphs tight
        self._newline_regex = re.compile(r"\n{3,}")
        # Detects broken line-break hyphenations caused by margin alignment shifts in text
        self._hyphen_break_regex = re.compile(r"(\w+)-\n(\w+)")

    def clean(self, raw_text: str) -> str:
        """
        Runs the raw text string through the full structural validation cleaning chain.

        Args:
            raw_text: The messy string string extracted from a source document.

        Returns:
            A sanitized, normalized text string.
        """
        if not raw_text:
            return ""

        # 1. Strip raw binary control sequences
        cleaned = self._control_char_regex.sub("", raw_text)

        # 2. Re-stitch words separated by line-break hyphenations
        cleaned = self._hyphen_break_regex.sub(r"\1\2", cleaned)

        # 3. Enforce deterministic Unicode representation structure
        cleaned = unicodedata.normalize(self.config.normalize_unicode_form, cleaned)

        # 4. Strip accents and diacritics if explicitly toggled on
        if self.config.strip_accents:
            cleaned = "".join(
                char for char in unicodedata.normalize("NFD", cleaned)
                if unicodedata.category(char) != "Mn"
            )

        # 5. Collapse multi-line layout gaps
        cleaned = self._newline_regex.sub("\n\n", cleaned)

        # 6. Collapse consecutive horizontal spacer padding elements
        if self.config.remove_extra_whitespace:
            # Clean spaces row-by-row to avoid destroying logical structural lines
            lines = [self._whitespace_regex.sub(" ", line).strip() for line in cleaned.splitlines()]
            cleaned = "\n".join(lines)

        # 7. Convert text to lowercase if configuration is enabled
        if self.config.lowercase:
            cleaned = cleaned.lower()

        return cleaned.strip()

    def clean_batch(self, texts: list[str]) -> list[str]:
        """
        Helper method to apply cleaning logic across collections of text chunks.

        Args:
            texts: List of messy input strings.

        Returns:
            List of successfully sanitized strings.
        """
        logger.debug(f"Initiating cleaning process pass over a batch collection of {len(texts)} text elements.")
        return [self.clean(text) for text in texts]