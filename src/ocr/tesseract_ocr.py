"""Tesseract OCR engine wrapper for the KMRL Platform.

A lightweight alternative / fallback to the PaddleOCR engine, backed by the Tesseract
binary via ``pytesseract``. Mirrors the ``PaddleOCRWrapper`` surface (``extract_text``
and ``process_layout``) so the two are interchangeable in the ingestion pipeline.

The ``pytesseract`` / Pillow imports are deferred to construction time so this module can
be imported without those (optional) dependencies installed.
"""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field

from config.logging import get_logger

logger = get_logger(__name__)


class OCRResultItem(BaseModel):
    """A single recognized text region with its confidence and bounding box."""
    text: str = Field(..., description="The recognized text content.")
    confidence: float = Field(default=0.0, description="Recognition confidence in the range 0..1.")
    box: List[List[int]] = Field(
        default_factory=list,
        description="Bounding polygon as [[x0,y0],[x1,y1],[x2,y2],[x3,y3]].",
    )


class TesseractOCRWrapper:
    """Thin wrapper around Tesseract exposing a Paddle-compatible interface."""

    def __init__(self, lang: str = "eng") -> None:
        try:
            import pytesseract  # type: ignore
        except ImportError as error:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Tesseract OCR requires the 'pytesseract' package and the Tesseract binary."
            ) from error
        self._pytesseract = pytesseract
        self.lang = lang
        logger.info("TesseractOCRWrapper initialized (lang=%s).", lang)

    def extract_text(self, image: Any) -> str:
        """Run OCR on a Pillow image and return a flat, whitespace-joined string."""
        try:
            text = self._pytesseract.image_to_string(image, lang=self.lang)
            return " ".join(text.split())
        except Exception as error:  # pragma: no cover - degrade gracefully like PaddleOCR
            logger.exception("Tesseract text extraction failed: %s", error)
            return ""

    def process_layout(self, image: Any) -> List[OCRResultItem]:
        """Run OCR and return per-word items with confidence and bounding boxes."""
        try:
            data = self._pytesseract.image_to_data(
                image, lang=self.lang, output_type=self._pytesseract.Output.DICT
            )
        except Exception as error:  # pragma: no cover
            logger.exception("Tesseract layout extraction failed: %s", error)
            return []

        items: List[OCRResultItem] = []
        n = len(data.get("text", []))
        for i in range(n):
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                conf = -1.0
            if conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            items.append(
                OCRResultItem(
                    text=word,
                    confidence=conf / 100.0,
                    box=[[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                )
            )
        return items
