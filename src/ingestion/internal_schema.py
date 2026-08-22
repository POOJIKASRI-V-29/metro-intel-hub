from pydantic import BaseModel
from typing import List, Optional

class PageResult(BaseModel):
    page_number: int
    text: str
    used_ocr: bool

class PDFResult(BaseModel):
    full_text: str
    page_count: int
    used_ocr: bool
    pages: List[PageResult]

class ProcessedDocument(BaseModel):
    filename: str
    full_text: str
    metadata: dict

class Chunk(BaseModel):
    text: str
    metadata: dict