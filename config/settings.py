"""Application-wide configuration for the KMRL Document Intelligence Platform.

This module defines a single, strongly-typed, environment-driven settings
object that every other layer of the application (ingestion, OCR,
preprocessing, embeddings, LLM, retrieval, agents, knowledge graph,
pipelines, and API) reads from. No module should read `os.environ`
directly -- all runtime configuration must flow through `get_settings()`.

Typical usage example:

    from config.settings import get_settings

    settings = get_settings()
    print(settings.app.app_name)
    print(settings.llm.active_provider)
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from typing_extensions import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment identifiers.

    Attributes:
        DEVELOPMENT: Local developer machine.
        STAGING: Pre-production environment used for integration testing.
        PRODUCTION: Live enterprise deployment.
        TEST: Automated test execution (pytest).
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LLMProvider(str, Enum):
    """Supported LLM backends.

    Attributes:
        OLLAMA: Local Ollama server exposing an OpenAI-compatible API.
        OPENAI_COMPATIBLE: Any hosted OpenAI-compatible endpoint
            (OpenAI itself, Azure OpenAI, vLLM, LM Studio, etc.).
    """

    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class OCRProvider(str, Enum):
    """Supported OCR engines.

    Attributes:
        PADDLE: PaddleOCR (default, better multi-lingual + layout support).
        TESSERACT: Tesseract OCR (lightweight fallback).
    """

    PADDLE = "paddle"
    TESSERACT = "tesseract"


class AppSettings(BaseSettings):
    """Core application metadata and runtime behaviour.

    Attributes:
        app_name: Human-readable name of the service.
        app_version: Semantic version string, surfaced on /health and /docs.
        environment: Current deployment environment.
        debug: Enables verbose error responses and auto-reload behaviour.
            Must never be True in PRODUCTION (enforced by validator).
    """

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    app_name: str = Field(default="KMRL Document Intelligence Platform")
    app_version: str = Field(default="0.1.0")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)

    @model_validator(mode="after")
    def _forbid_debug_in_production(self) -> "AppSettings":
        """Ensures debug mode is never enabled in production.

        Returns:
            The validated AppSettings instance.

        Raises:
            ValueError: If `debug=True` while `environment=PRODUCTION`.
        """
        if self.environment == Environment.PRODUCTION and self.debug:
            raise ValueError("APP_DEBUG must be False when APP_ENVIRONMENT=production")
        return self


class ServerSettings(BaseSettings):
    """FastAPI / Uvicorn server and networking configuration.

    Attributes:
        host: Bind address for the API server.
        port: Bind port for the API server.
        cors_origins: List of allowed CORS origins. Use ["*"] only in
            development.
        api_prefix: URL prefix applied to all registered routers.
        request_timeout_seconds: Hard timeout for a single API request,
            used by upstream middleware / reverse proxies.
    """

    model_config = SettingsConfigDict(env_prefix="SERVER_", extra="ignore")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    api_prefix: str = Field(default="/api/v1")
    request_timeout_seconds: int = Field(default=120, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allows CORS origins to be supplied as a comma-separated string.

        Args:
            value: Raw value from the environment, either a comma-separated
                string (e.g. "http://a.com,http://b.com") or an already
                parsed list.

        Returns:
            A list of origin strings.
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


class LLMSettings(BaseSettings):
    """LLM provider configuration supporting both Ollama and OpenAI-compatible backends.

    The active backend is selected via `active_provider`. Only the fields
    relevant to the selected provider are validated as mandatory; the
    other provider's fields may remain at their defaults.

    Attributes:
        active_provider: Which backend `llm/llm_client.py` should use.
        ollama_base_url: Base URL of the local/remote Ollama server.
        ollama_model: Model tag pulled/served by Ollama (e.g. "llama3.1:8b").
        openai_base_url: Base URL for any OpenAI-compatible endpoint.
        openai_api_key: API key/bearer token for the OpenAI-compatible endpoint.
        openai_model: Model name to request from the OpenAI-compatible endpoint.
        temperature: Sampling temperature applied to generation calls.
        max_output_tokens: Upper bound on generated tokens per call.
        request_timeout_seconds: Per-request HTTP timeout to the LLM backend.
        max_retries: Number of retry attempts on transient LLM failures.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    active_provider: LLMProvider = Field(default=LLMProvider.OLLAMA)

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")

    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")

    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=1)
    request_timeout_seconds: int = Field(default=60, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)

    @model_validator(mode="after")
    def _require_api_key_for_openai_compatible(self) -> "LLMSettings":
        """Ensures an API key is present when the OpenAI-compatible provider is active.

        Returns:
            The validated LLMSettings instance.

        Raises:
            ValueError: If `active_provider=OPENAI_COMPATIBLE` and
                `openai_api_key` is not set.
        """
        if self.active_provider == LLMProvider.OPENAI_COMPATIBLE and not self.openai_api_key:
            raise ValueError(
                "LLM_OPENAI_API_KEY must be set when LLM_ACTIVE_PROVIDER=openai_compatible"
            )
        return self


class EmbeddingSettings(BaseSettings):
    """HuggingFace Sentence-Transformers embedding configuration.

    Attributes:
        model_name: HuggingFace model identifier or local path.
        device: Torch device to load the model on ("cpu", "cuda", "mps").
        batch_size: Number of texts embedded per forward pass.
        normalize_embeddings: Whether to L2-normalize output vectors
            (required for cosine similarity search).
        cache_dir: Directory used for on-disk embedding cache.
        vector_dimension: Expected output dimensionality of the model,
            used to validate the vector store schema at startup.
    """

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", extra="ignore")

    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    device: str = Field(default="cpu")
    batch_size: int = Field(default=32, ge=1)
    normalize_embeddings: bool = Field(default=True)
    cache_dir: Path = Field(default=Path("./data/embedding_cache"))
    vector_dimension: int = Field(default=384, ge=1)


class VectorStoreSettings(BaseSettings):
    """ChromaDB vector store configuration.

    Attributes:
        enabled: Feature flag. When False, `embeddings/vector_store.py`
            must fail fast with a clear error rather than silently no-op.
        persist_directory: On-disk location for ChromaDB's persistent client.
        collection_name: Name of the default document chunk collection.
        host: Optional remote ChromaDB server host (if not using embedded mode).
        port: Optional remote ChromaDB server port.
    """

    model_config = SettingsConfigDict(env_prefix="VECTOR_DB_", extra="ignore")

    enabled: bool = Field(default=True)
    persist_directory: Path = Field(default=Path("./data/chroma"))
    collection_name: str = Field(default="kmrl_documents")
    host: Optional[str] = Field(default=None)
    port: Optional[int] = Field(default=None, ge=1, le=65535)


class GraphSettings(BaseSettings):
    """Neo4j knowledge graph configuration.

    Attributes:
        enabled: Feature flag. When False, `knowledge_graph/*` modules
            must fail fast with a clear error rather than silently no-op.
        uri: Bolt URI of the Neo4j instance (e.g. "bolt://localhost:7687").
        user: Neo4j username.
        password: Neo4j password.
        database: Target Neo4j database name.
        max_connection_pool_size: Driver-level connection pool size.
    """

    model_config = SettingsConfigDict(env_prefix="GRAPH_", extra="ignore")

    enabled: bool = Field(default=False)
    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: Optional[str] = Field(default=None)
    database: str = Field(default="neo4j")
    max_connection_pool_size: int = Field(default=50, ge=1)

    @model_validator(mode="after")
    def _require_credentials_when_enabled(self) -> "GraphSettings":
        """Ensures Neo4j credentials are present when the graph feature is enabled.

        Returns:
            The validated GraphSettings instance.

        Raises:
            ValueError: If `enabled=True` and `password` is not set.
        """
        if self.enabled and not self.password:
            raise ValueError("GRAPH_PASSWORD must be set when GRAPH_ENABLED=true")
        return self


class OCRSettings(BaseSettings):
    """OCR engine configuration used by `ocr/` and `ingestion/image_parser.py`.

    Attributes:
        provider: Which OCR engine to use by default.
        languages: Language codes passed to the OCR engine (PaddleOCR
            style, e.g. ["en"], ["en", "hi"]).
        use_gpu: Whether to run the OCR engine on GPU if available.
        confidence_threshold: Minimum confidence to accept an OCR token.
    """

    model_config = SettingsConfigDict(env_prefix="OCR_", extra="ignore")

    provider: OCRProvider = Field(default=OCRProvider.PADDLE)
    languages: Annotated[List[str], NoDecode] = Field(default_factory=lambda: ["en"])
    use_gpu: bool = Field(default=False)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("languages", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allows OCR languages to be supplied as a comma-separated string.

        Args:
            value: Raw value from the environment, either a comma-separated
                string (e.g. "en,hi") or an already parsed list.

        Returns:
            A list of language codes.
        """
        if isinstance(value, str):
            return [lang.strip() for lang in value.split(",") if lang.strip()]
        return value


class ChunkingSettings(BaseSettings):
    """Text chunking defaults used by `preprocessing/chunker.py`.

    Attributes:
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks in characters.
        min_chunk_size: Minimum viable chunk size; smaller trailing chunks
            are merged into the previous chunk.
    """

    model_config = SettingsConfigDict(env_prefix="CHUNK_", extra="ignore")

    chunk_size: int = Field(default=1000, ge=50)
    chunk_overlap: int = Field(default=150, ge=0)
    min_chunk_size: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def _validate_overlap_smaller_than_size(self) -> "ChunkingSettings":
        """Ensures overlap never exceeds or equals the chunk size.

        Returns:
            The validated ChunkingSettings instance.

        Raises:
            ValueError: If `chunk_overlap >= chunk_size`.
        """
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_CHUNK_OVERLAP must be smaller than CHUNK_CHUNK_SIZE")
        return self


class RetrievalSettings(BaseSettings):
    """Hybrid retrieval and re-ranking defaults used by `retrieval/`.

    Attributes:
        top_k: Number of results returned to the caller after re-ranking.
        candidate_pool_size: Number of candidates pulled from each of the
            semantic and BM25 searches before fusion/re-ranking.
        semantic_weight: Weight of semantic search in hybrid score fusion.
        bm25_weight: Weight of BM25 search in hybrid score fusion.
        reranker_model_name: Cross-encoder model used for re-ranking.
        reranker_enabled: Feature flag to bypass re-ranking (e.g. for speed).
        duplicate_similarity_threshold: Cosine similarity above which two
            chunks are considered near-duplicates.
    """

    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_", extra="ignore")

    top_k: int = Field(default=5, ge=1)
    candidate_pool_size: int = Field(default=25, ge=1)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    bm25_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    reranker_model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    reranker_enabled: bool = Field(default=True)
    duplicate_similarity_threshold: float = Field(default=0.97, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_weights_sum_to_one(self) -> "RetrievalSettings":
        """Ensures hybrid search weights combine to a normalized total of 1.0.

        Returns:
            The validated RetrievalSettings instance.

        Raises:
            ValueError: If `semantic_weight + bm25_weight` is not
                approximately 1.0 (tolerance 1e-6).
        """
        total = self.semantic_weight + self.bm25_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "RETRIEVAL_SEMANTIC_WEIGHT + RETRIEVAL_BM25_WEIGHT must sum to 1.0"
            )
        return self


class UploadSettings(BaseSettings):
    """File upload constraints used by `ingestion/validator.py` and the upload route.

    Attributes:
        max_file_size_mb: Maximum accepted upload size in megabytes.
        allowed_extensions: Whitelisted file extensions (lowercase, with dot).
        upload_dir: Directory where raw uploaded files are persisted.
    """

    model_config = SettingsConfigDict(env_prefix="UPLOAD_", extra="ignore")

    max_file_size_mb: int = Field(default=25, ge=1)
    allowed_extensions: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"]
    )
    upload_dir: Path = Field(default=Path("./data/uploads"))

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allows allowed extensions to be supplied as a comma-separated string.

        Args:
            value: Raw value from the environment, either a comma-separated
                string (e.g. ".pdf,.docx") or an already parsed list.

        Returns:
            A list of lowercase extensions.
        """
        if isinstance(value, str):
            return [ext.strip().lower() for ext in value.split(",") if ext.strip()]
        return value

    @property
    def max_file_size_bytes(self) -> int:
        """Computes the maximum upload size in bytes.

        Returns:
            The configured max file size converted to bytes.
        """
        return self.max_file_size_mb * 1024 * 1024


class LoggingSettings(BaseSettings):
    """Logging level and sink configuration consumed by `config/logging_config.py`.

    Attributes:
        level: Root log level (e.g. "DEBUG", "INFO", "WARNING", "ERROR").
        json_format: When True, emit structured JSON logs (recommended for
            production log aggregation); when False, emit human-readable
            console logs (recommended for local development).
        log_file: Optional path to a rotating log file. If None, logs are
            written to stdout only.
    """

    model_config = SettingsConfigDict(env_prefix="LOG_", extra="ignore")

    level: str = Field(default="INFO")
    json_format: bool = Field(default=False)
    log_file: Optional[Path] = Field(default=None)

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        """Validates that the configured log level is a recognized Python logging level.

        Args:
            value: Raw log level string from the environment.

        Returns:
            The upper-cased, validated log level string.

        Raises:
            ValueError: If the value is not a standard logging level name.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_value = value.upper()
        if upper_value not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {value!r}")
        return upper_value


class Settings(BaseSettings):
    """Root settings object aggregating every configuration section.

    This is the single object that should be imported (via `get_settings()`)
    throughout the codebase. Each nested section is independently loaded
    from environment variables / a `.env` file using its own prefix, which
    keeps configuration organized while still supporting a single
    `Settings()` construction call.

    Attributes:
        app: Core application metadata.
        server: API server and networking configuration.
        llm: LLM provider configuration.
        embedding: Sentence-transformer embedding configuration.
        vector_store: ChromaDB configuration.
        graph: Neo4j configuration.
        ocr: OCR engine configuration.
        chunking: Text chunking configuration.
        retrieval: Hybrid retrieval and re-ranking configuration.
        upload: File upload constraints.
        logging: Logging configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app: AppSettings = Field(default_factory=AppSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    graph: GraphSettings = Field(default_factory=GraphSettings)
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    def ensure_runtime_directories(self) -> None:
        """Creates all filesystem directories referenced by settings, if missing.

        This should be called once during application startup (see
        `api/main.py`'s startup event) so that downstream modules can
        assume these paths already exist.

        Returns:
            None.
        """
        directories: List[Path] = [
            self.upload.upload_dir,
            self.embedding.cache_dir,
        ]
        if self.vector_store.enabled:
            directories.append(self.vector_store.persist_directory)
        if self.logging.log_file is not None:
            directories.append(self.logging.log_file.parent)

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
class FeatureFlagSettings(BaseSettings):
    """Per-capability feature toggles for the KMRL platform.

    These flags let individual capabilities be disabled independently of
    the two core storage backends (`VectorStoreSettings.enabled` and
    `GraphSettings.enabled`), which remain the authoritative switches for
    ChromaDB and Neo4j respectively. A capability flag being True does not
    override a disabled storage backend it depends on -- see
    `_validate_dependencies` below.

    Attributes:
        enable_vector_search: Toggles the semantic/BM25/hybrid search
            capability exposed via `retrieval/` and `api/routes/search.py`.
        enable_chat: Toggles the RAG chat capability
            (`retrieval/rag_pipeline.py`, `api/routes/chat.py`).
        enable_summarization: Toggles `agents/summarizer_agent.py` and
            `api/routes/summarize.py`.
        enable_metadata_extraction: Toggles `agents/metadata_agent.py` and
            `preprocessing/metadata_extractor.py` integration into pipelines.
        enable_duplicate_detection: Toggles `retrieval/duplicate_detector.py`.
        enable_recommendations: Toggles `retrieval/recommendation_engine.py`.
        enable_graph_features: Toggles knowledge-graph-backed API surface
            (`agents/graph_agent.py`, `api/routes/graph.py`). Requires
            `GraphSettings.enabled` to also be True.
        enable_multi_agent: Toggles the LangGraph multi-agent workflow
            (`agents/workflow.py`); when False, pipelines should fall back
            to direct single-agent calls instead of the full graph.
        enable_classification: Toggles `agents/classifier_agent.py` and
            `api/routes/classify.py`.
    """

    model_config = SettingsConfigDict(env_prefix="FEATURE_", extra="ignore")

    enable_vector_search: bool = Field(default=True)
    enable_chat: bool = Field(default=True)
    enable_summarization: bool = Field(default=True)
    enable_metadata_extraction: bool = Field(default=True)
    enable_duplicate_detection: bool = Field(default=True)
    enable_recommendations: bool = Field(default=True)
    enable_graph_features: bool = Field(default=False)
    enable_multi_agent: bool = Field(default=True)
    enable_classification: bool = Field(default=True)

    feature_flags: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)

    @model_validator(mode="after")
    def _validate_feature_dependencies(self) -> "Settings":
        """Ensures capability flags are consistent with backend flags.

        Returns:
            The validated Settings instance.

        Raises:
            ValueError: If `FEATURE_ENABLE_GRAPH_FEATURES=true` while
                `GRAPH_ENABLED=false`, or if
                `FEATURE_ENABLE_VECTOR_SEARCH`/`FEATURE_ENABLE_CHAT`/
                `FEATURE_ENABLE_RECOMMENDATIONS` is true while
                `VECTOR_DB_ENABLED=false`.
        """
        if self.feature_flags.enable_graph_features and not self.graph.enabled:
            raise ValueError(
                "FEATURE_ENABLE_GRAPH_FEATURES requires GRAPH_ENABLED=true"
            )
        vector_dependent_flags = {
            "FEATURE_ENABLE_VECTOR_SEARCH": self.feature_flags.enable_vector_search,
            "FEATURE_ENABLE_CHAT": self.feature_flags.enable_chat,
            "FEATURE_ENABLE_RECOMMENDATIONS": self.feature_flags.enable_recommendations,
        }
        if not self.vector_store.enabled:
            active_dependents = [name for name, value in vector_dependent_flags.items() if value]
            if active_dependents:
                raise ValueError(
                    f"{active_dependents} require VECTOR_DB_ENABLED=true"
                )
        return self
def get_settings() -> Settings:
    """Returns a cached, process-wide singleton of the application settings.

    Using `lru_cache` guarantees that environment variables and the `.env`
    file are parsed exactly once per process, and that every module
    receives the same validated configuration object.

    Returns:
        The singleton `Settings` instance.

    Example:
        >>> from config.settings import get_settings
        >>> settings = get_settings()
        >>> settings.server.port
        8000
    """
    
    return Settings()
"""Centralized logging configuration for the KMRL Document Intelligence Platform.

This module must be configured exactly once, at process startup (typically
from `api/main.py`'s startup event, or at the top of a standalone script /
pytest `conftest.py`). After `configure_logging()` has run, every other
module should obtain its logger via:

    from config.logging_config import get_logger
    logger = get_logger(__name__)

No module should call `logging.basicConfig()` or attach handlers directly.

Typical usage example:

    from config.logging_config import configure_logging, get_logger

    configure_logging()
    logger = get_logger(__name__)
    logger.info("Application startup complete")
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import LoggingSettings, get_settings

_CONFIGURED: bool = False
"""Module-level guard preventing duplicate handler attachment on repeated calls."""


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Intended for production environments where logs are shipped to an
    aggregator (e.g. ELK, Loki, CloudWatch) that expects structured input.

    Attributes:
        None. This formatter is stateless beyond what `logging.Formatter`
        already tracks.
    """

    _RESERVED_ATTRS = frozenset(
        {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """Renders a single log record as a JSON string.

        Args:
            record: The log record emitted by a logger.

        Returns:
            A single-line JSON string representing the record, including
            any `extra=` fields passed by the caller, and a formatted
            exception traceback if present.
        """
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include any caller-supplied `extra={...}` fields.
        for key, value in record.__dict__.items():
            if key not in self._RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for local development.

    Produces lines like:
        2026-07-08 14:32:01 | INFO     | ingestion.pdf_parser | Parsed 12 pages
    """

    _FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        """Initializes the formatter with the fixed console format string."""
        super().__init__(fmt=self._FORMAT, datefmt=self._DATE_FORMAT)


def _build_handlers(settings: LoggingSettings) -> list[logging.Handler]:
    """Builds the list of logging handlers based on configured settings.

    Args:
        settings: The validated `LoggingSettings` section.

    Returns:
        A list containing a stdout `StreamHandler`, and, if `log_file` is
        set, an additional `RotatingFileHandler`. Both handlers share the
        same formatter (JSON or console) determined by `settings.json_format`.
    """
    formatter: logging.Formatter = (
        JSONFormatter() if settings.json_format else ConsoleFormatter()
    )

    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if settings.log_file is not None:
        log_path: Path = settings.log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    return handlers


def configure_logging(settings: Optional[LoggingSettings] = None, force: bool = False) -> None:
    """Configures the root logger for the entire application process.

    Idempotent by default: calling this more than once is a no-op unless
    `force=True`, which prevents duplicate handlers being attached if
    multiple entry points (e.g. `api/main.py` and a test fixture) both
    call it.

    Args:
        settings: An explicit `LoggingSettings` instance to use. If None,
            the value is pulled from `get_settings().logging`.
        force: When True, reconfigures the root logger even if
            `configure_logging` has already run in this process. Useful
            in pytest when a test needs a different log level.

    Returns:
        None.

    Example:
        >>> from config.logging_config import configure_logging
        >>> configure_logging()
    """
    global _CONFIGURED

    if _CONFIGURED and not force:
        return

    resolved_settings: LoggingSettings = settings or get_settings().logging

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_settings.level)

    # Clear any pre-existing handlers to avoid duplicate log lines on
    # reconfiguration (relevant when force=True, e.g. in tests).
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)

    for handler in _build_handlers(resolved_settings):
        root_logger.addHandler(handler)

    # Quiet down noisy third-party libraries by default; individual
    # modules can still raise these back up via LOG_LEVEL if needed.
    for noisy_logger_name in ("httpx", "httpcore", "urllib3", "sentence_transformers"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger, configuring the root logger first if needed.

    This is the function every module in the codebase should call instead
    of `logging.getLogger()` directly, since it guarantees
    `configure_logging()` has run at least once (using default settings)
    even if the caller forgot to invoke it explicitly at startup.

    Args:
        name: The logger name, conventionally `__name__` of the calling
            module (e.g. "ingestion.pdf_parser").

    Returns:
        A configured `logging.Logger` instance.

    Example:
        >>> from config.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Started processing", extra={"document_id": "doc_123"})
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
