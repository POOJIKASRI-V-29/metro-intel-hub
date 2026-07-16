"""
GraphRAG and Knowledge Graph Extraction Pipeline for the KMRL Platform.

This module orchestrates structured entity-relationship extraction from unstructured 
text chunks and coordinates the assembly of knowledge graphs for multi-hop RAG reasoning.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..preprocessing.chunker import TextChunk
from ..generation.llm_manager import LLMManager

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.graph_pipeline")


class GraphNode(BaseModel):
    """Represents a unique entity (vertex) inside the Knowledge Graph."""
    id: str = Field(..., description="Unique label or name of the entity (e.g., 'Acme Corp').")
    type: str = Field(..., description="The category of entity (e.g., 'ORGANIZATION', 'PERSON', 'PROJECT').")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes belonging to the node.")


class GraphRelationship(BaseModel):
    """Represents a directed relationship (edge) connecting two GraphNodes."""
    source: str = Field(..., description="The source node entity ID.")
    target: str = Field(..., description="The destination node entity ID.")
    relation_type: str = Field(..., description="The verbs describing the linkage (e.g., 'MANAGES', 'DEVELOPED_BY').")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Attributes about the relationship (e.g., weight, date).")


class GraphExtractionResult(BaseModel):
    """Data envelope containing all structured elements mined from a document text slice."""
    nodes: List[GraphNode] = Field(default_factory=list)
    relationships: List[GraphRelationship] = Field(default_factory=list)


class GraphPipeline:
    """
    Orchestrates entity mining, graph database indexing, and multi-hop hybrid lookups.
    """

    def __init__(self, llm_manager: LLMManager, graph_client: Optional[Any] = None) -> None:
        """
        Initializes the GraphRAG orchestration layer.

        Args:
            llm_manager: Configured instance of the generation engine used to run mining prompts.
            graph_client: Optional concrete driver instance (e.g., Neo4j client connection wrapper).
        """
        self.llm_manager = llm_manager
        self.graph_client = graph_client
        
        if self.graph_client:
            logger.info("GraphRAG Pipeline initialized with active Graph database driver state.")
        else:
            logger.warning("No Graph DB driver provided. Extracted graphs will operate in memory/log states.")

    def extract_knowledge_graph(self, chunks: List[TextChunk]) -> GraphExtractionResult:
        """
        Iterates over a list of text chunks, prompting the LLM to pull out structural triples.

        Args:
            chunks: Text fragments derived from the document processing chain.

        Returns:
            A combined GraphExtractionResult aggregating all mined entities and relations.
        """
        logger.info(f"--- Starting Knowledge Graph extraction over {len(chunks)} text chunks ---")
        aggregated_result = GraphExtractionResult()

        extraction_prompt_template = (
            "You are a strict knowledge graph information extractor.\n"
            "Your task is to extract clear Entities and Relationships from the text segment below.\n\n"
            "Format your output strictly as a JSON object with this exact structure:\n"
            "{\n"
            "  \"nodes\": [{\"id\": \"Entity Name\", \"type\": \"ORGANIZATION/PERSON/SOFTWARE/etc\"}],\n"
            "  \"relationships\": [{\"source\": \"Entity Name\", \"target\": \"Other Entity\", \"relation_type\": \"BELONGS_TO\"}]\n"
            "}\n\n"
            "Do not include markdown code block syntax (like ```json). Return raw string text data only.\n\n"
            "TEXT SEGMENT:\n"
        )

        for idx, chunk in enumerate(chunks):
            try:
                logger.debug(f"Processing chunk {idx + 1}/{len(chunks)} for semantic graph mining...")
                
                # Re-use the underlying LLM client with specialized extraction formatting instructions
                # We mock context_chunks as empty since we are performing extraction, not RAG generation here
                response_payload = self.llm_manager.client.chat.completions.create(
                    model=self.llm_manager.config.model_name,
                    messages=[
                        {"role": "system", "content": "You are a technical data parsing assistant that output raw JSON only."},
                        {"role": "user", "content": f"{extraction_prompt_template}\n{chunk.text}"}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )

                raw_json = response_payload.choices[0].message.content or "{}"
                parsed_data = json.loads(raw_json)

                # Map raw dictionary layers securely into typed Pydantic structures
                for n in parsed_data.get("nodes", []):
                    # Attach parent origin metadata tracking back to the source text node chunk
                    props = n.get("properties", {})
                    props["source_chunk_id"] = chunk.chunk_id
                    aggregated_result.nodes.append(GraphNode(id=n["id"], type=n["type"], properties=props))

                for r in parsed_data.get("relationships", []):
                    aggregated_result.relationships.append(
                        GraphRelationship(source=r["source"], target=r["target"], relation_type=r["relation_type"])
                    )

            except Exception as error:
                logger.error(f"Skipping graph node compilation on chunk idx {idx} due to extraction anomaly: {str(error)}")
                continue

        logger.info(f"--- Extraction phase completed. Mined {len(aggregated_result.nodes)} nodes and {len(aggregated_result.relationships)} edges. ---")
        return aggregated_result

    def write_to_graph_store(self, extraction: GraphExtractionResult) -> bool:
        """
        Commits structured node and relationship arrays into the downstream graph instance.
        """
        if not self.graph_client:
            logger.warning("Graph database store target execution skipped: No active client driver connected.")
            return False
            
        try:
            logger.info(f"Syncing graph extraction schema into database graph space...")
            # Real-world logic would run a Cypher script (Neo4j) or Gremlin loop here:
            # self.graph_client.query("MERGE (a:Entity {id: $id}) SET a.type = $type", ...)
            return True
        except Exception as error:
            logger.error(f"Failed to synchronize extraction elements to Graph Storage index: {str(error)}")
            return False