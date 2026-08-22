"""
Graph Visualization Engine for the KMRL Knowledge Graph Layer.

Converts internal graph data structures into standardized, UI-consumable 
JSON matrices or graph-theory formats optimized for frontend render pipelines.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("document_intelligence.knowledge_graph.graph_visualizer")


class GraphVisualizer:
    """
    Transforms network topologies into standardized interchange representations
    for interactive rendering and analytical plotting.
    """

    def __init__(self) -> None:
        """
        Initializes configuration properties for category color mappings and scales.
        """
        # Dictionary establishing group identifiers for frontend styling engines
        self.category_groups: Dict[str, int] = {
            "ORGANIZATION": 1,
            "PERSON": 2,
            "TECHNOLOGY": 3,
            "CONCEPT": 4,
            "LOCATION": 5
        }
        logger.info("GraphVisualizer successfully initialized with categorical style groups.")

    def _get_group_id(self, entity_type: str) -> int:
        """ Maps entity types to consistent group numbers for visualization clusters. """
        return self.category_groups.get(entity_type.upper(), 0)

    def generate_d3_payload(self, graph_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Converts internal graph structures into the explicit node-link format 
        required by data visualization frameworks like D3.js, Vis.js, or Cytoscape.

        Args:
            graph_data: A dictionary containing 'nodes' and 'edges' lists from the query engine.

        Returns:
            A dictionary matching the structural schema:
            {
                "nodes": [{"id": str, "label": str, "group": int, "value": float}],
                "links": [{"source": str, "target": str, "label": str, "weight": float}]
            }
        """
        raw_nodes: List[Dict[str, Any]] = graph_data.get("nodes", [])
        raw_edges: List[Dict[str, Any]] = graph_data.get("edges", [])

        logger.debug(f"Compiling interactive graph payload for {len(raw_nodes)} nodes and {len(raw_edges)} edges.")

        formatted_nodes: List[Dict[str, Any]] = []
        formatted_links: List[Dict[str, Any]] = []

        # Step 1: Serialize node instances into discrete UI configurations
        for node in raw_nodes:
            display_name = node.get("display_name", "Unknown Node")
            # Create a unique node key matching the ingestion pattern
            node_id = " ".join(display_name.strip().upper().split())

            formatted_nodes.append({
                "id": node_id,
                "label": display_name,
                "type": node.get("type", "UNKNOWN"),
                "group": self._get_group_id(node.get("type", "UNKNOWN")),
                "description": node.get("description", ""),
                "size_weight": node.get("importance_score", 0.5)
            })

        # Step 2: Normalize directional edge segments into node-link references
        for edge in raw_edges:
            source_raw = edge.get("source_entity", "")
            target_raw = edge.get("target_entity", "")

            # Ensure endpoints match normalized string keys exactly
            source_id = " ".join(source_raw.strip().upper().split())
            target_id = " ".join(target_raw.strip().upper().split())

            formatted_links.append({
                "source": source_id,
                "target": target_id,
                "label": edge.get("relation_type", "RELATED_TO"),
                "description": edge.get("description", ""),
                "weight": edge.get("strength", 1.0)
            })

        logger.info("Successfully exported network topology into a standard D3 node-link layout configuration.")
        return {
            "nodes": formatted_nodes,
            "links": formatted_links
        }

    def render_ascii_tree(self, graph_data: Dict[str, Any], root_entity_name: str) -> str:
        """
        Generates a quick-view ASCII tree representation of immediate relationships. 
        Highly useful for debugging graph connections straight from a terminal log.
        """
        root_key = " ".join(root_entity_name.strip().upper().split())
        raw_edges = graph_data.get("edges", [])
        
        lines = [f"🌲 Root Graph Element: [{root_entity_name.upper()}]"]
        match_found = False

        for edge in raw_edges:
            s_key = " ".join(edge.get("source_entity", "").strip().upper().split())
            if s_key == root_key:
                match_found = True
                relation = edge.get("relation_type", "LINKS_TO")
                target = edge.get("target_entity", "UNKNOWN")
                strength = edge.get("strength", 1.0)
                lines.append(f" └── ──({relation:.<16})──> [{target}] (w={strength})")

        if not match_found:
            lines.append(" └── (No outgoing relational edges found in current sub-context)")

        return "\n".join(lines)