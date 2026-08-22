import os
import logging
from .pdf_reader import PDFReader
from .docx_reader import DocxReader
from .image_reader import ImageReader
from api.schemas.internal_schema import ProcessedDocument

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.docx_reader = DocxReader()
        self.image_reader = ImageReader()

    def process_document(self, file_path: str) -> ProcessedDocument:
        """Orchestrates document extraction based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        
        full_text = ""
        metadata = {"source": filename, "extension": ext}

        if ext == ".pdf":
            result = self.pdf_reader.extract_pdf(file_path)
            full_text = result.full_text
            metadata["page_count"] = result.page_count
            metadata["used_ocr"] = result.used_ocr
        elif ext in [".docx", ".doc"]:
            full_text = self.docx_reader.extract_docx(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
            full_text = self.image_reader.extract_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        return ProcessedDocument(
            filename=filename,
            full_text=full_text,
            metadata=metadata
        )