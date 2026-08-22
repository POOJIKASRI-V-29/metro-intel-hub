"""
Relationship Builder Engine for the KMRL Knowledge Graph Layer.

Orchestrates the extraction of semantic edges (relationships) between previously 
identified entities within a text chunk, outputting directional node linkages.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..llm.llm_client import LLMClient
from ..llm.response_formatter import LLMResponseFormatter
from ..llm.response_parser import LLMResponseParser
from .entity_extractor import ExtractedEntity

logger = logging.getLogger("document_intelligence.knowledge_graph.relationship_builder")


class ExtractedRelationship(BaseModel):
    """Data frame representing a single directional edge between two graph nodes."""
    source_entity: str = Field(..., description="The exact name of the origin node, matching an extracted entity.")
    target_entity: str = Field(..., description="The exact name of the destination node, matching an extracted entity.")
    relation_type: str = Field(..., description="A capitalized, underscored action verb classification (e.g., FOUNDED_BY, ACQUIRED, USES_TECHNOLOGY).")
    description: str = Field(..., description="A short factual explanation of how these two entities relate in the text.")
    strength: float = Field(..., description="Confidence or magnitude score of this relationship from 0.0 to 1.0.")


class RelationshipExtractionSchema(BaseModel):
    """Schema container forcing the LLM to yield collections of relational edges."""
    relationships: List[ExtractedRelationship] = Field(..., description="A definitive collection of all logical relationships detected.")


class RelationshipBuilder:
    """
    Manages the evaluation of text fragments to map directional, weighted edges 
    between established semantic nodes.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initializes the edge extraction builder with an established LLM execution client interface.
        """
        self.llm_client = llm_client
        self.parser = LLMResponseParser()
        
        self.system_prompt = (
            "You are an advanced graph topology engine. Your task is to extract directional "
            "relationships between a specific list of provided entities based ONLY on the provided text.\n"
            "CRITICAL EXTRACTION LAWS:\n"
            "1. ONLY create relationships where both the source and target exist in the provided entity list.\n"
            "2. Use UPPERCASE_WITH_UNDERSCORES for the relation_type (e.g., DEVELOPED_BY, SUBSIDIARY_OF).\n"
            "3. Ensure the direction of the relationship makes logical sense (A -> B).\n"
            "4. Provide a brief description and a relationship strength score (0.0 to 1.0)."
        )
        logger.info("GraphRAG RelationshipBuilder initialized with strict edge routing constraints.")

    def extract_edges(self, chunk_text: str, available_entities: List[ExtractedEntity]) -> List[ExtractedRelationship]:
        """
        Processes a text segment alongside its known entities to map relational linkages.

        Args:
            chunk_text: The target text segment providing the semantic context.
            available_entities: The list of nodes already parsed from this text.

        Returns:
            A list of validated ExtractedRelationship instances.
        """
        if not chunk_text or not available_entities:
            logger.warning("Empty text or missing entity anchor list. Skipping relationship extraction.")
            return []

        # Isolate just the names to act as the strict vocabulary for the LLM
        entity_names = [entity.name for entity in available_entities]
        logger.debug(f"Dispatching edge extraction loop across {len(entity_names)} anchor nodes.")

        # Construct the context payload ensuring the LLM knows its boundaries
        user_prompt = (
            f"AVAILABLE ENTITIES TO LINK:\n{', '.join(entity_names)}\n\n"
            f"TEXT SEGMENT TO PARSE:\n{chunk_text}"
        )

        structured_config = LLMResponseFormatter.get_structured_output_config(RelationshipExtractionSchema)

        try:
            raw_output = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                extra_params={"response_format": structured_config}
            )

            parsed_payload = self.parser.parse_to_pydantic(raw_output, RelationshipExtractionSchema)
            
            # Post-processing validation to drop hallucinations where the LLM invented a new node
            valid_edges = []
            normalized_anchors = {name.lower() for name in entity_names}
            
            for edge in parsed_payload.relationships:
                if edge.source_entity.lower() in normalized_anchors and edge.target_entity.lower() in normalized_anchors:
                    valid_edges.append(edge)
                else:
                    logger.debug(f"Dropped hallucinated edge referencing unknown node: {edge.source_entity} -> {edge.target_entity}")

            logger.info(f"Successfully isolated {len(valid_edges)} validated relational edges from text chunk.")
            return valid_edges

        except Exception as err:
            logger.error(f"Structured relationship extraction pass failed: {str(err)}")
            return []