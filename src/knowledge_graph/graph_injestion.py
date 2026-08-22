"""
Graph Ingestion Engine for the KMRL Knowledge Graph Layer.

Coordinates node mapping workflows, handling concept upsert transactions, 
deduplication mechanics, and document provenance attachments.
"""

import logging
from typing import Any, Dict, List, Optional
from .entity_extractor import ExtractedEntity

logger = logging.getLogger("document_intelligence.knowledge_graph.graph_ingestion")


class GraphIngestionEngine:
    """
    Manages state synchronization, mapping individual entity blocks onto 
    a centralized, deduplicated persistent knowledge matrix.
    """

    def __init__(self) -> None:
        """
        Initializes an in-memory transactional storage mirror for the graph nodes.
        In a cloud deployment, this layer interfaces with an external cluster (e.g., Neo4j or AWS Neptune).
        """
        # Node index mapping uniquely identified entity names to attribute structures
        self.nodes_registry: Dict[str, Dict[str, Any]] = {}
        # Tracks document origin links to preserve data lineage boundaries
        self.provenance_registry: Dict[str, List[str]] = {}
        
        logger.info("GraphIngestionEngine initialized with local deduplication caching active.")

    def _normalize_key(self, name: str) -> str:
        """
        Normalizes character frames to ensure deterministic deduplication mapping matches.
        """
        return " ".join(name.strip().upper().split())

    def upsert_entities(self, entities: List[ExtractedEntity], source_document_id: str) -> int:
        """
        Safely registers or merges a collection of extracted graph nodes, adjusting 
        importance scores dynamically and updating provenance links.

        Args:
            entities: An array of validated entities parsed by extraction steps.
            source_document_id: The unique identifier tracking the source file.

        Returns:
            The total count of distinct nodes processed during the transaction.
        """
        if not entities:
            return 0

        processed_count = 0
        logger.debug(f"Starting transactional ingestion for {len(entities)} nodes from document: {source_document_id}")

        for entity in entities:
            node_key = self._normalize_key(entity.name)
            
            # If the node already exists, safely merge attribute metrics rather than duplicating the element
            if node_key in self.nodes_registry:
                existing_node = self.nodes_registry[node_key]
                # Keep the descriptive frame that contains more descriptive detail
                if len(entity.description) > len(existing_node["description"]):
                    existing_node["description"] = entity.description
                
                # Smooth importance scores across duplicate references via moving maximum calculations
                existing_node["importance_score"] = max(existing_node["importance_score"], entity.importance_score)
                logger.debug(f"Merged attributes onto existing graph concept node: '{node_key}'")
            else:
                # Create a completely fresh node record structure inside our registry
                self.nodes_registry[node_key] = {
                    "display_name": entity.name,
                    "type": entity.type.upper(),
                    "description": entity.description,
                    "importance_score": entity.importance_score
                }
                logger.debug(f"Created primary node mapping entry for concept: '{node_key}'")

            # Update document tracking arrays to ensure clean lineage trails
            if node_key not in self.provenance_registry:
                self.provenance_registry[node_key] = []
                
            if source_document_id not in self.provenance_registry[node_key]:
                self.provenance_registry[node_key].append(source_document_id)

            processed_count += 1

        logger.info(f"Successfully synchronized graph transaction. Ingested nodes count: {processed_count}")
        return processed_count

    def get_node_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves specific details and origin listings for a given entry.
        """
        node_key = self._normalize_key(entity_name)
        base_node = self.nodes_registry.get(node_key)
        
        if not base_node:
            return None
            
        return {
            **base_node,
            "origin_documents": self.provenance_registry.get(node_key, [])
        }