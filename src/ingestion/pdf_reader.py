"""
PDF Extraction module for the KMRL Document Intelligence Platform.

This module leverages PyMuPDF to efficiently extract text and page-level metadata
from PDF files or raw binary memory streams.
"""

import io
import logging
from typing import BinaryIO, List
import fitz  # type: ignore # PyMuPDF
from pydantic import BaseModel, Field

# Setup logger matching enterprise configuration
logger = logging.getLogger("document_intelligence.ingestion.pdf_parser")


class ParsedPage(BaseModel):
    """
    Data model representing a single successfully parsed PDF page.
    """
    page_number: int = Field(..., description="The 1-based page index.")
    text: str = Field(..., description="The raw textual content extracted from the page.")
    width: float = Field(..., description="Width of the page in points.")
    height: float = Field(..., description="Height of the page in points.")


class PdfParser:
    """
    Handles high-performance text extraction from PDF files and memory streams.
    """

    def __init__(self) -> None:
        """Initializes the PDF parser component."""
        pass

    def parse_stream(self, file_stream: BinaryIO) -> List[ParsedPage]:
        """
        Parses a raw binary file stream containing PDF data and extracts its content.

        Args:
            file_stream: A seekable file-like binary object containing a PDF.

        Returns:
            A list of ParsedPage objects containing text and structural metrics.

        Raises:
            ValueError: If the file is corrupted, encrypted, or invalid.
        """
        try:
            # Read stream into bytes to initialize PyMuPDF memory document
            file_stream.seek(0)
            stream_bytes = file_stream.read()
            
            parsed_pages: List[ParsedPage] = []
            
            # Context manager for the fitz document to guarantee memory cleanup
            with fitz.open(stream=stream_bytes, filetype="pdf") as doc:
                if doc.is_encrypted:
                    logger.error("PDF parsing failed: Document is password protected or encrypted.")
                    raise ValueError("Cannot parse encrypted PDF documents.")

                if doc.page_count == 0:
                    logger.warning("PDF document contains zero pages.")
                    return parsed_pages

                logger.info(f"Successfully loaded PDF document containing {doc.page_count} pages.")

                for page_idx, page in enumerate(doc):
                    # Extract text using 'text' layout mode which preserves flow order
                    text_content = page.get_text("text")
                    rect = page.rect

                    parsed_pages.append(
                        ParsedPage(
                            page_number=page_idx + 1,
                            text=text_content,
                            width=rect.width,
                            height=rect.height
                        )
                    )

            return parsed_pages

        except fitz.FileDataError as error:
            logger.exception("PyMuPDF failed to process structural PDF binary data.")
            raise ValueError("The provided stream is not a valid or readable PDF document.") from error
        except Exception as error:
            if not isinstance(error, ValueError):
                logger.exception("An unhandled error occurred during PDF stream extraction.")
                raise ValueError("An internal error occurred while parsing the PDF document.") from error
            raise

    def parse_file(self, file_path: str) -> List[ParsedPage]:
        """
        Parses a PDF file located directly on the local file system.

        Args:
            file_path: The absolute or relative string path to the PDF file.

        Returns:
            A list of ParsedPage objects containing text and structural metrics.

        Raises:
            ValueError: If the file path is invalid, unreadable, or corrupted.
        """
        try:
            parsed_pages: List[ParsedPage] = []

            with fitz.open(file_path) as doc:
                if doc.is_encrypted:
                    logger.error(f"PDF parsing failed: File at '{file_path}' is encrypted.")
                    raise ValueError("Cannot parse encrypted PDF files.")

                for page_idx, page in enumerate(doc):
                    text_content = page.get_text("text")
                    rect = page.rect

                    parsed_pages.append(
                        ParsedPage(
                            page_number=page_idx + 1,
                            text=text_content,
                            width=rect.width,
                            height=rect.height
                        )
                    )

            return parsed_pages

        except FileNotFoundError:
            logger.error(f"PDF file not found at path: {file_path}")
            raise ValueError(f"File not found at target path: {file_path}")
        except fitz.FileDataError as error:
            logger.exception(f"PyMuPDF structural layout failure for file: {file_path}")
            raise ValueError(f"Corrupt or invalid PDF file layout at: {file_path}") from error
        except Exception as error:
            if not isinstance(error, ValueError):
                logger.exception(f"Unexpected error when reading disk PDF file: {file_path}")
                raise ValueError(f"Failed to process file at path: {file_path}") from error
            raise