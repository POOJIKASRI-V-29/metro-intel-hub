"""
Analytics and Telemetry Pipeline for the KMRL Platform.

This module provides a centralized ingestion point for platform metrics, 
tracking token consumption, search query trends, and retrieval latencies.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.analytics_pipeline")


class RAGTelemetryEvent(BaseModel):
    """
    Standardized schema for recording a single RAG interaction event.
    """
    event_id: str = Field(..., description="Unique identifier for the specific API transaction.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC time of the event.")
    user_id: str = Field(default="anonymous", description="Identifier of the user requesting the action.")
    query_text: str = Field(..., description="The raw textual search or chat question.")
    
    # Retrieval Metrics
    retrieved_chunk_count: int = Field(default=0, description="How many context chunks were fetched.")
    retrieval_latency_ms: float = Field(default=0.0, description="Time taken to query the vector database in milliseconds.")
    
    # Generation Metrics
    model_used: Optional[str] = Field(default=None, description="The specific LLM utilized.")
    prompt_tokens: int = Field(default=0, description="Number of tokens consumed in the prompt/context.")
    completion_tokens: int = Field(default=0, description="Number of tokens consumed to generate the answer.")
    generation_latency_ms: float = Field(default=0.0, description="Time taken by the LLM to stream the full response.")

    # Application State
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom tags, such as department ID or frontend client version.")


class AnalyticsPipeline:
    """
    Orchestrates the asynchronous collection and routing of platform telemetry.
    """

    def __init__(self, backend_dsn: Optional[str] = None) -> None:
        """
        Initializes the analytics pipeline.

        Args:
            backend_dsn: Optional connection string for a dedicated telemetry database 
                         (e.g., PostgreSQL, Datadog, or Elasticsearch).
        """
        self.backend_dsn = backend_dsn
        
        if self.backend_dsn:
            logger.info(f"Analytics Pipeline initialized. Telemetry routed to backend: {self.backend_dsn}")
        else:
            logger.warning("No backend DSN provided. Analytics will be routed to standard standard-out logs natively.")

    def record_interaction(self, event: RAGTelemetryEvent) -> bool:
        """
        Processes and stores a complete RAG interaction event.

        Args:
            event: The fully populated RAGTelemetryEvent envelope.

        Returns:
            True if successfully recorded, False otherwise.
        """
        try:
            # Calculate total cost/tokens for immediate tracking
            total_tokens = event.prompt_tokens + event.completion_tokens
            
            # Formulate the payload
            payload = event.model_dump(mode="json")
            
            # Step 1: Write to the standard operational logger for immediate debugging
            logger.info(
                f"RAG Event [{event.event_id}] | User: {event.user_id} | "
                f"Tokens: {total_tokens} | Retrieval ms: {event.retrieval_latency_ms:.2f}"
            )

            # Step 2: Route to dedicated analytics backend (Mocked for architecture purposes)
            if self.backend_dsn:
                self._dispatch_to_warehouse(payload)
                
            return True

        except Exception as error:
            # We never want analytics tracking failures to crash the main application
            logger.error(f"Failed to record analytics telemetry event: {str(error)}")
            return False

    def _dispatch_to_warehouse(self, payload: Dict[str, Any]) -> None:
        """
        Internal stub method to handle network dispatch to systems like Postgres or Datadog.
        """
        # Example: requests.post(f"{self.backend_dsn}/v1/events", json=payload)
        logger.debug(f"Dispatched telemetry payload to data warehouse. Size: {len(str(payload))} bytes.")