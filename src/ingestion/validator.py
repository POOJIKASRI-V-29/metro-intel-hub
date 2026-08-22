"""
Document validation module for the KMRL Document Intelligence Platform.

This module enforces enterprise limits on file uploads, including file size constraints,
strict extension whitelisting, and deep magic-byte validation to prevent extension spoofing.
"""

import logging
from pathlib import Path
from typing import BinaryIO, Dict, Set
from pydantic import BaseModel, Field

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.ingestion.validator")


class ValidationConfig(BaseModel):
    """
    Configuration properties for document validation rules.
    """
    max_file_size_bytes: int = Field(
        default=52428800,  # 50 MB default limit
        description="Maximum allowed file size in bytes."
    )
    allowed_extensions: Set[str] = Field(
        default={".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".xlsx", ".xls"},
        description="Set of permitted lower-case file extensions including the leading dot."
    )


class DocumentValidator:
    """
    Handles validation of files based on sizing, naming, and structure.
    """

    # Hex signatures (magic bytes) for common enterprise formats to block spoofing
    MAGIC_SIGNATURES: Dict[bytes, str] = {
        b"%PDF": ".pdf",
        b"PK\x03\x04": ".docx",  # OpenXML format (DOCX, XLSX)
        b"\x89PNG\r\n\x1a\n": ".png",
        b"\xff\xd8\xff": ".jpg"   # Covers JPEG/JPG
    }

    def __init__(self, config: ValidationConfig | None = None) -> None:
        """
        Initializes the validator with configuration rules.

        Args:
            config: Optional configuration override object.
        """
        self.config = config or ValidationConfig()

    def validate_size(self, file_size: int) -> bool:
        """
        Validates that the file size does not exceed corporate thresholds.

        Args:
            file_size: Size of the file in bytes.

        Returns:
            True if within acceptable limits.

        Raises:
            ValueError: If file size is less than or equal to 0, or exceeds max limit.
        """
        if file_size <= 0:
            logger.error("Validation failed: File is completely empty (0 bytes).")
            raise ValueError("File cannot be empty.")

        if file_size > self.config.max_file_size_bytes:
            max_mb = self.config.max_file_size_bytes / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            logger.error(f"Validation failed: File size ({actual_mb:.2f} MB) exceeds limit ({max_mb:.2f} MB).")
            raise ValueError(f"File size exceeds maximum permitted limit of {max_mb:.1f} MB.")

        return True

    def validate_extension(self, filename: str) -> str:
        """
        Validates that the file extension is inside the approved whitelist.

        Args:
            filename: The full name or path string of the file.

        Returns:
            The normalized lower-case extension string (e.g., '.pdf').

        Raises:
            ValueError: If the extension is empty or not in the whitelist.
        """
        path = Path(filename)
        extension = path.suffix.lower()

        if not extension:
            logger.error(f"Validation failed: Filename '{filename}' does not contain an extension.")
            raise ValueError("Filename must have a valid extension.")

        if extension not in self.config.allowed_extensions:
            logger.error(f"Validation failed: Extension '{extension}' is not supported.")
            raise ValueError(f"Unsupported file extension '{extension}'.")

        return extension

    def validate_content_integrity(self, file_stream: BinaryIO, expected_extension: str) -> bool:
        """
        Inspects the leading binary bytes of a file stream to verify internal consistency.
        Prevents security risks such as executing malicious scripts disguised as .pdf or .docx.

        Args:
            file_stream: A seekable file-like binary stream.
            expected_extension: The verified extension from `validate_extension`.

        Returns:
            True if the binary headers match acceptable formats.

        Raises:
            ValueError: If file signatures do not match the declared extension.
        """
        try:
            # Save original stream pointer position
            original_position = file_stream.tell()
            file_stream.seek(0)
            
            # Read up to 8 bytes for signature scanning
            header_bytes = file_stream.read(8)
            
            # Return pointer to its original state to avoid side-effects down the pipeline
            file_stream.seek(original_position)

            # Special validation pass for formats we track via magic bytes
            matched_extension: str | None = None
            for signature, ext in self.MAGIC_SIGNATURES.items():
                if header_bytes.startswith(signature):
                    matched_extension = ext
                    break

            if matched_extension is not None:
                # Direct check or generic check for OpenXML containers (.docx and .xlsx share PK header)
                if matched_extension == ".docx" and expected_extension in {".docx", ".xlsx"}:
                    return True
                if matched_extension == expected_extension:
                    return True
                
                logger.error(
                    f"Spoofing attempt detected! Declared: {expected_extension}, Header matches: {matched_extension}"
                )
                raise ValueError("File content does not match its file extension declaration.")

            # Pass files we don't strictly index via magic bytes (like legacy .xls) but warn in logs
            logger.warning(f"File validation bypasses deep binary headers for extension type: {expected_extension}")
            return True

        except Exception as error:
            if not isinstance(error, ValueError):
                logger.exception("An unexpected error occurred during binary signature analysis.")
                raise ValueError("Could not read file stream signatures for verification.") from error
            raise