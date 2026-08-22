"""
Graph Query and Traversal Engine for the KMRL Knowledge Graph Layer.

Executes subgraph extraction, neighborhood expansion, and pathfinding queries 
to power hybrid GraphRAG context windows.
"""

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger("document_intelligence.knowledge_graph.graph_queries")


class GraphQueryEngine:
    """
    Handles read-only traversal operations over the knowledge graph topologies.
    """

    def __init__(
        self, 
        nodes_registry: Dict[str, Dict[str, Any]], 
        edges_registry: List[Dict[str, Any]]
    ) -> None:
        """
        Initializes the query engine with read access to the centralized graph state.
        
        Args:
            nodes_registry: Central dictionary of deduplicated entity nodes.
            edges_registry: Central array of directional relationship triples.
        """
        self.nodes = nodes_registry
        self.edges = edges_registry
        logger.info("GraphQueryEngine initialized with active read-state access.")

    def _normalize_key(self, name: str) -> str:
        """Normalizes lookup keys to match the ingestion layer format."""
        return " ".join(name.strip().upper().split())

    def get_node_neighborhood(
        self, 
        entity_names: List[str], 
        depth: int = 1,
        min_strength: float = 0.0
    ) -> Dict[str, Any]:
        """
        Extracts a localized subgraph centered around a list of target entities.

        Args:
            entity_names: Starting points for the neighborhood expansion.
            depth: How many relationship hops to traverse from the starting nodes.
            min_strength: Threshold to filter out weak or low-confidence edges.

        Returns:
            A dictionary containing the isolated 'nodes' and 'edges' of the neighborhood.
        """
        if not entity_names:
            return {"nodes": [], "edges": []}

        logger.debug(f"Executing {depth}-hop neighborhood traversal for {len(entity_names)} anchor nodes.")
        
        # Normalize seed keys to ensure exact matching against the registry
        current_frontier = {self._normalize_key(name) for name in entity_names}
        explored_nodes: Set[str] = set()
        captured_edges: List[Dict[str, Any]] = []

        for current_depth in range(depth):
            next_frontier: Set[str] = set()
            
            for edge in self.edges:
                # Filter out edges below the required confidence threshold
                if edge.get("strength", 0.0) < min_strength:
                    continue

                source_key = self._normalize_key(edge["source_entity"])
                target_key = self._normalize_key(edge["target_entity"])

                # If either end of the edge touches our current traversal frontier
                if source_key in current_frontier or target_key in current_frontier:
                    # Deduplicate edge capture
                    if edge not in captured_edges:
                        captured_edges.append(edge)
                        
                    # Add connected nodes to the next traversal wave
                    if source_key not in explored_nodes and source_key not in current_frontier:
                        next_frontier.add(source_key)
                    if target_key not in explored_nodes and target_key not in current_frontier:
                        next_frontier.add(target_key)

            # Mark current wave as explored and advance the frontier
            explored_nodes.update(current_frontier)
            current_frontier = next_frontier
            
            if not current_frontier:
                break  # Early exit if the expansion hits a dead end

        # Compile the final subgraph node payloads
        final_node_keys = explored_nodes.union(current_frontier)
        captured_nodes = [
            self.nodes[key] for key in final_node_keys if key in self.nodes
        ]

        logger.info(
            f"Traversal complete. Extracted subgraph containing {len(captured_nodes)} nodes "
            f"and {len(captured_edges)} edges."
        )
        
        return {
            "nodes": captured_nodes,
            "edges": captured_edges
        }

    def format_subgraph_for_llm(self, subgraph: Dict[str, Any]) -> str:
        """
        Translates a structured subgraph dictionary into a highly readable 
        text block optimized for injection into an LLM context window.
        """
        if not subgraph.get("nodes") and not subgraph.get("edges"):
            return "No relevant graph context found."

        context_lines = ["--- EXTRACTED KNOWLEDGE GRAPH FACTS ---"]
        
        for edge in subgraph.get("edges", []):
            source = edge.get("source_entity", "UNKNOWN")
            relation = edge.get("relation_type", "RELATED_TO")
            target = edge.get("target_entity", "UNKNOWN")
            desc = edge.get("description", "")
            
            fact_string = f"[{source}] --({relation})--> [{target}]"
            if desc:
                fact_string += f" (Context: {desc})"
                
            context_lines.append(fact_string)

        return "\n".join(context_lines)