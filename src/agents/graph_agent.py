"""Knowledge Graph Extraction Agent for the KMRL platform.

Scope: Analyzes raw text chunks to extract structured entities (nodes) 
and their semantic relationships (edges). This agent relies on a strict 
JSON schema to ensure the extracted data can be safely ingested into a 
graph database (like Neo4j or NetworkX).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Any, List

from config.logging import get_logger
from src.utils.constants import EntityType, RelationType

logger = get_logger(__name__)


@dataclass
class Entity:
    """Represents a node in the Knowledge Graph."""
    entity_id: str
    name: str
    type: EntityType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """Represents a directional edge between two entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    context: str = ""


@dataclass
class GraphExtractionResult:
    """Structured output containing all nodes and edges extracted from a text chunk."""
    entities: List[Entity]
    relationships: List[Relationship]


class GraphAgent:
    """Agent responsible for extracting graph structures from unstructured text.

    This class enforces strict prompt engineering to force the LLM to act as an 
    information extraction engine, outputting deterministic nodes and edges.
    """

    def __init__(self, llm_generate_fn: Callable[[str, str], str]) -> None:
        """Initializes the GraphAgent.

        Args:
            llm_generate_fn: A callable that accepts a (system_prompt, user_prompt) 
                and returns a raw text string from the LLM.
        """
        self.llm_generate = llm_generate_fn
        
        # dynamically load allowed enum values for the prompt
        self._valid_entity_types = [e.value for e in EntityType]
        self._valid_relation_types = [r.value for r in RelationType]
        
        self._system_prompt = (
            "You are an expert Knowledge Graph extraction engine. Your task is to analyze "
            "the provided text and extract entities and the relationships between them.\n\n"
            f"ALLOWED ENTITY TYPES: {self._valid_entity_types}\n"
            f"ALLOWED RELATION TYPES: {self._valid_relation_types}\n\n"
            "RULES:\n"
            "1. Output strictly valid JSON.\n"
            "2. Generate a unique 'entity_id' (e.g., 'e1', 'e2') for each entity.\n"
            "3. Relationships must use the generated 'entity_id's for 'source_id' and 'target_id'.\n"
            "4. Only extract explicit relationships mentioned in the text.\n\n"
            "EXPECTED JSON SCHEMA:\n"
            "{\n"
            '  "entities": [\n'
            '    {"entity_id": "str", "name": "str", "type": "str", "properties": {}}\n'
            '  ],\n'
            '  "relationships": [\n'
            '    {"source_id": "str", "target_id": "str", "relation_type": "str", "context": "str"}\n'
            '  ]\n'
            "}"
        )
        logger.debug("GraphAgent initialized with entity and relation constraints.")

    def extract_graph_data(self, text: str) -> GraphExtractionResult:
        """Analyzes text to extract nodes and edges.

        Args:
            text: The raw document text or chunk to process.

        Returns:
            A GraphExtractionResult dataclass containing entities and relationships.
            
        Raises:
            ValueError: If the text is empty or parsing fails completely.
        """
        if not text or not text.strip():
            logger.warning("GraphAgent received empty text. Returning empty graph.")
            return GraphExtractionResult(entities=[], relationships=[])

        user_prompt = f"--- TEXT TO ANALYZE ---\n{text}\n\nExtract entities and relationships."
        
        try:
            logger.debug(f"Dispatching graph extraction request (Text length: {len(text)}).")
            raw_response = self.llm_generate(self._system_prompt, user_prompt)
            return self._parse_response(raw_response)
        except Exception as exc:
            logger.error(f"GraphAgent execution failed: {exc}")
            # Fail closed: return an empty graph result rather than crashing the pipeline
            return GraphExtractionResult(entities=[], relationships=[])

    def _parse_response(self, response_text: str) -> GraphExtractionResult:
        """Extracts and validates the JSON payload from the LLM's response."""
        clean_text = response_text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            parsed_data: dict[str, Any] = json.loads(clean_text.strip())
            
            entities: List[Entity] = []
            relationships: List[Relationship] = []

            # Parse Entities
            for ent_data in parsed_data.get("entities", []):
                try:
                    e_type = EntityType(ent_data.get("type"))
                    entities.append(Entity(
                        entity_id=ent_data["entity_id"],
                        name=ent_data["name"],
                        type=e_type,
                        properties=ent_data.get("properties", {})
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid entity in LLM response: {ent_data} - Error: {e}")

            # Parse Relationships
            for rel_data in parsed_data.get("relationships", []):
                try:
                    r_type = RelationType(rel_data.get("relation_type"))
                    relationships.append(Relationship(
                        source_id=rel_data["source_id"],
                        target_id=rel_data["target_id"],
                        relation_type=r_type,
                        context=rel_data.get("context", "")
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid relationship in LLM response: {rel_data} - Error: {e}")

            return GraphExtractionResult(entities=entities, relationships=relationships)

        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(f"Failed to parse LLM graph response: {exc}. Raw: {response_text}")
            return GraphExtractionResult(entities=[], relationships=[])