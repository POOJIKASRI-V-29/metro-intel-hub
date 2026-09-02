"""
Document Loader Orchestrator for the KMRL Document Intelligence Platform.

This module implements the central orchestrator that applies dependency injection 
to manage validators and multiple document type parsers, delivering a single unified
data output contract to the preprocessing pipeline.
"""

import logging
import uuid
from typing import Any, BinaryIO, Dict, List, Optional
from pydantic import BaseModel, Field

# Relative sub-module imports within the ingestion folder
from .validator import DocumentValidator
from .pdf_reader import PdfParser
from .docx_reader import DocxParser
from .image_reader import ImageParser
from .excelparser import ExcelParser

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.ingestion.document_loader")


class ContentBlock(BaseModel):
    """
    Unified representation of text extracted from any document type.
    """
    text: str = Field(..., description="The raw textual fragment or segment.")
    page_or_element_index: int = Field(..., description="The original sequence position (e.g., page number, row index).")
    block_type: str = Field(..., description="The nature of the block (e.g., 'page', 'paragraph', 'table_row', 'sheet_markdown').")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Parser-specific spatial or layout metrics.")


class UnifiedDocumentPayload(BaseModel):
    """
    The canonical data contract produced by the ingestion layer.
    """
    document_id: str = Field(..., description="Unique UUID tracking the document lifecycle.")
    filename: str = Field(..., description="Original name of the uploaded document file.")
    extension: str = Field(..., description="Validated extension string, including leading dot.")
    content_blocks: List[ContentBlock] = Field(..., description="Ordered list of extracted text blocks.")


class DocumentLoader:
    """
    Unified orchestrator managing validation and parsing pathways for all document types.
    """

    def __init__(
        self,
        validator: Optional[DocumentValidator] = None,
        pdf_parser: Optional[PdfParser] = None,
        docx_parser: Optional[DocxParser] = None,
        image_parser: Optional[ImageParser] = None,
        excel_parser: Optional[ExcelParser] = None
    ) -> None:
        """
        Initializes the loader with required validator and parser engines via Dependency Injection.

        Args:
            validator: Validator instance. Defaults to standard configuration if None.
            pdf_parser: PDF processing engine instance.
            docx_parser: Microsoft Word processing engine instance.
            image_parser: Image processing and baseline OCR engine instance.
            excel_parser: Spreadsheet processing engine instance.
        """
        self.validator = validator or DocumentValidator()
        self.pdf_parser = pdf_parser or PdfParser()
        self.docx_parser = docx_parser or DocxParser()
        self.image_parser = image_parser or ImageParser()
        self.excel_parser = excel_parser or ExcelParser()

    def load_from_stream(self, file_stream: BinaryIO, filename: str, file_size: int) -> UnifiedDocumentPayload:
        """
        Validates an incoming binary stream and coordinates processing through the matching parser.

        Args:
            file_stream: A seekable file-like binary stream object.
            filename: The plain string filename declared during upload.
            file_size: Total file capacity in bytes.

        Returns:
            A UnifiedDocumentPayload containing completely mapped, linear text blocks.

        Raises:
            ValueError: If file fails validation bounds or lacks an eligible parser routing path.
        """
        try:
            # 1. Enforce validation invariants
            self.validator.validate_size(file_size)
            target_ext = self.validator.validate_extension(filename)
            self.validator.validate_content_integrity(file_stream, target_ext)

            document_id = str(uuid.uuid4())
            blocks: List[ContentBlock] = []

            logger.info(f"Routing document stream '{filename}' [{target_ext}] to its corresponding parsing engine.")

            # 2. Dynamic routing based on extension type
            if target_ext == ".pdf":
                pdf_pages = self.pdf_parser.parse_stream(file_stream)
                for page in pdf_pages:
                    blocks.append(
                        ContentBlock(
                            text=page.text,
                            page_or_element_index=page.page_number,
                            block_type="page",
                            extra_metadata={"width": page.width, "height": page.height}
                        )
                    )

            elif target_ext in {".docx", ".doc"}:
                docx_elements = self.docx_parser.parse_stream(file_stream)
                for elem in docx_elements:
                    blocks.append(
                        ContentBlock(
                            text=elem.text,
                            page_or_element_index=elem.index,
                            block_type=elem.element_type,
                            extra_metadata={}
                        )
                    )

            elif target_ext in {".png", ".jpg", ".jpeg"}:
                parsed_img = self.image_parser.parse_stream(file_stream)
                blocks.append(
                    ContentBlock(
                        text=parsed_img.text,
                        page_or_element_index=1,
                        block_type="ocr_frame",
                        extra_metadata={
                            "width": parsed_img.width,
                            "height": parsed_img.height,
                            "format": parsed_img.format
                        }
                    )
                )

            elif target_ext in {".xlsx", ".xls"}:
                parsed_sheets = self.excel_parser.parse_stream(file_stream)
                for s_idx, sheet in enumerate(parsed_sheets, start=1):
                    # We store the pre-compiled sheet markdown table representation as a core text block
                    blocks.append(
                        ContentBlock(
                            text=sheet.combined_markdown,
                            page_or_element_index=s_idx,
                            block_type="sheet_markdown",
                            extra_metadata={"sheet_name": sheet.sheet_name}
                        )
                    )

            else:
                logger.error(f"Unmapped routing attempt discovered for extension type: {target_ext}")
                raise ValueError(f"No active parser is registered to handle extension type '{target_ext}'")

            logger.info(f"Ingestion completed for doc reference {document_id}. Extracted {len(blocks)} blocks.")
            
            return UnifiedDocumentPayload(
                document_id=document_id,
                filename=filename,
                extension=target_ext,
                content_blocks=blocks
            )

        except Exception as error:
            if not isinstance(error, ValueError):
                logger.exception(f"Unexpected operational failure during stream orchestration of file: {filename}")
                raise ValueError(f"Failed to process document stream for file '{filename}'.") from error
            raise