"""
Image parsing and OCR module for the KMRL Document Intelligence Platform.

This module utilizes Pillow (PIL) for image handling and Tesseract as a baseline OCR
to extract text from scanned documents, diagrams, and photographs. It is designed 
with dependency injection to allow seamless swapping to advanced engines like PaddleOCR.
"""

import io
import logging
from typing import Any, BinaryIO, Callable, Optional
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

# Tesseract is an optional dependency (see requirements.txt). Importing this module must
# not require it, so document types that need no OCR (PDF, DOCX, XLSX) still ingest on
# hosts without the OCR stack installed.
try:
    import pytesseract  # type: ignore
except ImportError:
    pytesseract = None

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.ingestion.image_parser")


class ParsedImage(BaseModel):
    """
    Data model representing a successfully parsed and OCR'd image.
    """
    text: str = Field(..., description="The textual content extracted via OCR.")
    width: int = Field(..., description="Width of the image in pixels.")
    height: int = Field(..., description="Height of the image in pixels.")
    format: str = Field(..., description="The detected image format (e.g., JPEG, PNG).")


class ImageParser:
    """
    Handles image loading, metadata extraction, and Optical Character Recognition (OCR).
    """

    def __init__(self, ocr_engine: Optional[Callable[[Image.Image], str]] = None) -> None:
        """
        Initializes the Image parser with an optional injected OCR engine.

        Args:
            ocr_engine: A callable that takes a PIL Image and returns a text string.
                        If None, defaults to the built-in standard Tesseract engine.
        """
        self.ocr_engine = ocr_engine or self._default_tesseract_ocr

    def _default_tesseract_ocr(self, image: Image.Image) -> str:
        """
        Fallback default OCR implementation using PyTesseract.

        Args:
            image: A loaded PIL Image object.

        Returns:
            Extracted text string.
            
        Raises:
            RuntimeError: If the 'pytesseract' package or the Tesseract binary is
                not installed or accessible on the host.
        """
        if pytesseract is None:
            logger.error("The 'pytesseract' package is not installed in the execution scope.")
            raise RuntimeError(
                "OCR Engine failure: 'pytesseract' is not installed. Install it (and the "
                "Tesseract binary) to ingest images, or inject a different ocr_engine."
            )

        try:
            return pytesseract.image_to_string(image).strip()
        except pytesseract.TesseractNotFoundError as error:
            logger.error("Tesseract-OCR binary is not installed or not in the system PATH.")
            raise RuntimeError("OCR Engine failure: Tesseract is missing from the host system.") from error
        except Exception as error:
            logger.exception("Unexpected error during Tesseract OCR execution.")
            raise RuntimeError("OCR Engine failure during text extraction.") from error

    def parse_stream(self, file_stream: BinaryIO) -> ParsedImage:
        """
        Parses an in-memory binary stream containing image data.

        Args:
            file_stream: A seekable file-like binary object containing the image.

        Returns:
            A ParsedImage object containing the extracted text and image metadata.

        Raises:
            ValueError: If the stream does not contain valid image data.
        """
        try:
            file_stream.seek(0)
            stream_bytes = file_stream.read()
            memory_buffer = io.BytesIO(stream_bytes)
            
            with Image.open(memory_buffer) as img:
                # Force loading into memory to ensure the file is completely valid
                img.verify()
            
            # Re-open after verify() as verify() leaves the file pointer at the end
            memory_buffer.seek(0)
            with Image.open(memory_buffer) as img:
                return self._extract_content(img)

        except UnidentifiedImageError as error:
            logger.error("Failed to identify image from the provided memory stream.")
            raise ValueError("The stream does not contain a recognizable image format.") from error
        except Exception as error:
            if not isinstance(error, (ValueError, RuntimeError)):
                logger.exception("An unhandled error occurred during image stream parsing.")
                raise ValueError("An internal error occurred while parsing the image stream.") from error
            raise

    def parse_file(self, file_path: str) -> ParsedImage:
        """
        Parses an image file loaded directly from the local file system.

        Args:
            file_path: The absolute or relative string path to the image file.

        Returns:
            A ParsedImage object containing the extracted text and image metadata.

        Raises:
            ValueError: If the file path is invalid, unreadable, or corrupted.
        """
        try:
            with Image.open(file_path) as img:
                return self._extract_content(img)

        except FileNotFoundError:
            logger.error(f"Image file not found at path: {file_path}")
            raise ValueError(f"File not found at target path: {file_path}")
        except UnidentifiedImageError as error:
            logger.error(f"Failed to identify image format at path: {file_path}")
            raise ValueError(f"Invalid or corrupted image file at: {file_path}") from error
        except Exception as error:
            if not isinstance(error, (ValueError, RuntimeError)):
                logger.exception(f"Unexpected error reading image file: {file_path}")
                raise ValueError(f"Failed to process image file at path: {file_path}") from error
            raise

    def _extract_content(self, img: Image.Image) -> ParsedImage:
        """
        Internal worker that extracts structural metadata and executes OCR.

        Args:
            img: An open PIL Image object.

        Returns:
            A populated ParsedImage object.
        """
        # Extract metadata
        width, height = img.size
        img_format = img.format or "UNKNOWN"
        
        # Standardize image to RGB to prevent OCR issues with alpha channels (RGBA)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Execute dependency-injected OCR engine
        extracted_text = self.ocr_engine(img)

        logger.info(f"Successfully processed {img_format} image ({width}x{height}px).")

        return ParsedImage(
            text=extracted_text,
            width=width,
            height=height,
            format=img_format
        )