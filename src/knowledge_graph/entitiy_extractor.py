"""
Entity Extraction Engine for the KMRL Knowledge Graph Layer.

Leverages structured LLM generation passes to parse unstructured document 
text chunks into strongly typed entity nodes for GraphRAG injection.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..llm.llm_client import LLMClient
from ..llm.response_formatter import LLMResponseFormatter
from ..llm.response_parser import LLMResponseParser

logger = logging.getLogger("document_intelligence.knowledge_graph.entity_extractor")


class ExtractedEntity(BaseModel):
    """Data frame representing a single semantic entity node."""
    name: str = Field(..., description="The unique name identifier of the entity, normalized to Title Case.")
    type: str = Field(..., description="The classification category (e.g., ORGANIZATION, PERSON, TECHNOLOGY, CONCEPT).")
    description: str = Field(..., description="A brief summary of what this entity represents within the text context.")
    importance_score: float = Field(..., description="Relevance weight from 0.0 to 1.0 indicating significance in the chunk.")


class EntityExtractionSchema(BaseModel):
    """Schema container forcing the LLM to yield collections of entities."""
    entities: List[ExtractedEntity] = Field(..., description="A definitive collection of all distinct entities detected.")


class EntityExtractor:
    """
    Orchestrates grammar-constrained extraction loops to convert document text segments 
    into structured entity data records.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initializes the extractor with an established LLM execution client interface.
        """
        self.llm_client = llm_client
        self.parser = LLMResponseParser()
        
        # Define the foundational system guidelines for entity isolation
        self.system_prompt = (
            "You are an advanced information extraction engine designed to build technical knowledge graphs.\n"
            "Analyze the provided text fragment carefully and identify all notable entities.\n"
            "CRITICAL EXTRACTION LAWS:\n"
            "1. Normalize names to title case (e.g., 'OpenAI Inc' instead of 'openai inc').\n"
            "2. Filter out pronouns or overly generic words.\n"
            "3. Provide clean, factual descriptions based solely on the visible context.\n"
            "4. Assign an importance score reflecting how central the entity is to the core passage."
        )
        logger.info("GraphRAG EntityExtractor initialized with structured extraction constraints.")

    def extract_from_chunk(self, chunk_text: str) -> List[ExtractedEntity]:
        """
        Processes a single text chunk string and maps detected components onto node data records.

        Args:
            chunk_text: The target text segment to extract nodes from.

        Returns:
            A list of validated ExtractedEntity instances.
        """
        if not chunk_text or not chunk_text.strip():
            logger.warning("Received empty text segment input for extraction turn. Skipping processing loop.")
            return []

        logger.debug(f"Dispatching structured extraction sequence over a chunk of {len(chunk_text)} characters.")

        # Compile the Pydantic structural layout framework for strict schema parsing
        structured_config = LLMResponseFormatter.get_structured_output_config(EntityExtractionSchema)

        try:
            # Dispatch the completion request utilizing structured schema constraints
            raw_output = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_prompt=f"TEXT SEGMENT TO PARSE:\n{chunk_text}",
                extra_params={"response_format": structured_config}
            )

            # Pass raw tokens through the Pro parser to auto-heal minor JSON compilation anomalies
            parsed_payload = self.parser.parse_to_pydantic(raw_output, EntityExtractionSchema)
            
            logger.info(f"Successfully isolated {len(parsed_payload.entities)} graph entities from text chunk.")
            return parsed_payload.entities

        except Exception as err:
            logger.error(f"Structured entity extraction pass encountered an unrecoverable failure: {str(err)}")
            # Fallback to an empty list to prevent systemic ingestion batch failures
            return []