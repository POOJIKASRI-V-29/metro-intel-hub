"""Project-wide constant values shared across the KMRL platform.

Unlike `config/settings.py`, nothing here is environment-configurable --
these are fixed vocabularies and literals that must stay identical across
dev/staging/production. If a value should ever differ by environment, it
belongs in `settings.py` instead, not here.
"""

from __future__ import annotations

from enum import Enum


class DocumentCategory(str, Enum):
    """Fixed classification categories for `agents/classifier_agent.py`.

    Kept as a closed set so downstream consumers (routes, dashboards,
    evaluation scripts) can rely on an exhaustive, stable vocabulary.
    """

    ENGINEERING_DRAWING = "engineering_drawing"
    MAINTENANCE_REPORT = "maintenance_report"
    SAFETY_CIRCULAR = "safety_circular"
    REGULATORY_DIRECTIVE = "regulatory_directive"
    FINANCE_INVOICE = "finance_invoice"
    HR_POLICY = "hr_policy"
    BOARD_MINUTES = "board_minutes"
    VENDOR_CONTRACT = "vendor_contract"
    INCIDENT_REPORT = "incident_report"
    OTHER = "other"


class EntityType(str, Enum):
    """Named-entity types recognized by the knowledge graph extraction pipeline."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    DATE = "DATE"
    MONETARY_VALUE = "MONETARY_VALUE"
    REGULATION = "REGULATION"
    EQUIPMENT = "EQUIPMENT"
    PROJECT = "PROJECT"


class RelationType(str, Enum):
    """Relation types recognized by `knowledge_graph/relation_builder.py`."""

    ISSUED_BY = "ISSUED_BY"
    APPLIES_TO = "APPLIES_TO"
    REFERENCES = "REFERENCES"
    SUPERSEDES = "SUPERSEDES"
    RESPONSIBLE_FOR = "RESPONSIBLE_FOR"
    LOCATED_AT = "LOCATED_AT"
    DATED = "DATED"


class RiskSeverity(str, Enum):
    """Severity levels used by `agents/risk_agent.py`."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupportedMimeType(str, Enum):
    """Canonical MIME types recognized by `ingestion/validator.py`."""

    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    PNG = "image/png"
    JPEG = "image/jpeg"


EXTENSION_TO_MIME_TYPE: dict[str, SupportedMimeType] = {
    ".pdf": SupportedMimeType.PDF,
    ".docx": SupportedMimeType.DOCX,
    ".xlsx": SupportedMimeType.XLSX,
    ".xls": SupportedMimeType.XLS,
    ".png": SupportedMimeType.PNG,
    ".jpg": SupportedMimeType.JPEG,
    ".jpeg": SupportedMimeType.JPEG,
}
"""Maps a lowercase file extension (with leading dot) to its canonical MIME type."""


class ErrorCode(str, Enum):
    """Stable, machine-readable error codes returned in API error responses.

    These are distinct from HTTP status codes -- they let frontend/API
    consumers branch on a specific failure reason (e.g. show a "file too
    large" message) without parsing free-text error strings.
    """

    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    OCR_FAILED = "OCR_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    VECTOR_STORE_UNAVAILABLE = "VECTOR_STORE_UNAVAILABLE"
    GRAPH_STORE_UNAVAILABLE = "GRAPH_STORE_UNAVAILABLE"
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Default metadata field names extracted by `agents/metadata_agent.py`.
# Kept here (rather than hardcoded in the agent) so the prompt-building
# code in `config/prompts.py` and the parsing code in the agent always
# agree on the exact same field list.
DEFAULT_METADATA_FIELDS: tuple[str, ...] = (
    "title",
    "author",
    "department",
    "document_date",
    "reference_number",
    "confidentiality_level",
)

# Sentinel used across the ingestion/preprocessing layers to mark text
# that could not be extracted (e.g. OCR total failure) rather than using
# an empty string, which is ambiguous with "genuinely empty document".
UNEXTRACTABLE_TEXT_SENTINEL: str = "[UNEXTRACTABLE_CONTENT]"

# Standard key used in chunk metadata dicts across preprocessing,
# embeddings, and retrieval to reference the originating document's ID.
CHUNK_SOURCE_DOCUMENT_ID_KEY: str = "source_document_id"