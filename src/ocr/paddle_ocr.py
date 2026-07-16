"""
PaddleOCR wrapper module for the KMRL Document Intelligence Platform.

This module encapsulates the deep-learning-based PaddleOCR engine to perform high-fidelity
text detection, angle classification, and character recognition on complex enterprise documents.
"""

import logging
from typing import Any, Dict, List
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

# Try to import PaddleOCR safely to allow flexibility during deployment environments
try:
    from paddleocr import PaddleOCR as Engine  # type: ignore
except ImportError:
    Engine = None

# Setup logger matching Stage 0 configurations
logger = logging.getLogger("document_intelligence.ocr.paddle_ocr")


class OCRResultItem(BaseModel):
    """
    Data model representing a single recognized text bounding box from PaddleOCR.
    """
    text: str = Field(..., description="The recognized text string.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="The confidence score of the recognition.")
    bounding_box: List[List[float]] = Field(
        ..., 
        description="The four coordinate pairs [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] representing the box layout."
    )


class PaddleOCRWrapper:
    """
    Enterprise wrapper around the PaddleOCR engine to handle text detection and recognition.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True) -> None:
        """
        Initializes the PaddleOCR engine with localization and structural parameters.

        Args:
            lang: Language code for text recognition (defaults to 'en').
            use_angle_cls: Enables the direction/orientation classifier to fix rotated documents automatically.

        Raises:
            RuntimeError: If the paddleocr library is missing from the running environment.
        """
        if Engine is None:
            logger.error("PaddleOCR library is not installed in the current environment.")
            raise RuntimeError(
                "Missing dependency: Please install 'paddleocr' and its corresponding deep learning runtime."
            )

        try:
            logger.info(f"Initializing PaddleOCR instance (lang={lang}, use_angle_cls={use_angle_cls})...")
            # Initialize the internal engine. This downloads and caches weights automatically on first run.
            self._ocr_engine = Engine(lang=lang, use_angle_cls=use_angle_cls, show_log=False)
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as error:
            logger.exception("Failed to instantiate the underlying PaddleOCR deep learning models.")
            raise RuntimeError("OCR Engine initialization failure.") from error

    def extract_text(self, image: Image.Image) -> str:
        """
        Executes OCR on an image and returns a flat, space-separated string of all recognized text.

        Args:
            image: A PIL Image object.

        Returns:
            A clean, stripped string combining all detected text fragments.
        """
        results = self.process_layout(image)
        if not results:
            return ""
        
        return " ".join([item.text for item in results])

    def process_layout(self, image: Image.Image) -> List[OCRResultItem]:
        """
        Executes deep OCR processing on an image to return full text strings along with 
        their spatial bounding box configurations.

        Args:
            image: A PIL Image object.

        Returns:
            A list of OCRResultItem objects containing coordinates, text, and scores.
        """
        try:
            # 1. Convert PIL image layout into standard numpy uint8 format required by Paddle
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            img_ndarray = np.array(image)

            # 2. Execute inference through the Paddle pipeline
            # cls=True applies the angle classifier if use_angle_cls was set to True during init
            raw_results = self._ocr_engine.ocr(img_ndarray, cls=True)

            parsed_items: List[OCRResultItem] = []

            # PaddleOCR returns a nested list structure: [ [ [ [box], (text, score) ], ... ] ]
            # Under certain conditions or blank pages, it might return None or an empty outer list
            if not raw_results or raw_results[0] is None:
                logger.warning("PaddleOCR completed inference but found zero text segments.")
                return parsed_items

            for page_results in raw_results:
                for line in page_results:
                    box = line[0]        # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text_info = line[1]  # ("Recognized Text", 0.985)
                    
                    text_str = text_info[0].strip()
                    confidence_score = float(text_info[1])

                    parsed_items.append(
                        OCRResultItem(
                            text=text_str,
                            confidence=confidence_score,
                            bounding_box=box
                        )
                    )

            logger.info(f"PaddleOCR successfully extracted {len(parsed_items)} text boxes from image frame.")
            return parsed_items

        except Exception as error:
            logger.exception("An unhandled exception occurred during PaddleOCR inference execution.")
            # Gracefully degrade by returning an empty collection instead of crashing the pipeline
            return []