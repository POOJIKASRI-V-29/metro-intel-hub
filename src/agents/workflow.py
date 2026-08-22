"""Agent Workflow Orchestrator for the KMRL platform.

Scope: Chains together the specialized AI agents (Classifier, Metadata, 
Risk, Graph, and Storage) to process an ingested document sequentially. 
It aggregates the outputs from each agent into a unified representation 
ready for vector and graph database insertion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from config.logging import get_logger
from src.agents.classifier_agent import ClassifierAgent, ClassificationResult
from src.agents.metadata_agent import MetadataAgent, MetadataExtractionResult
from src.agents.risk_agent import RiskAgent, RiskAssessmentResult
from src.agents.graph_agent import GraphAgent, GraphExtractionResult
from src.agents.storage_agent import StorageAgent, StorageDecision

logger = get_logger(__name__)


@dataclass
class DocumentProcessingState:
    """Aggregated state holding the results of the agent workflow."""
    chunk_text: str
    classification: ClassificationResult | None = None
    metadata: MetadataExtractionResult | None = None
    risks: RiskAssessmentResult | None = None
    graph_data: GraphExtractionResult | None = None
    storage_decision: StorageDecision | None = None


class IngestionWorkflow:
    """Orchestrates the sequential execution of AI agents on document text."""

    def __init__(
        self,
        classifier: ClassifierAgent,
        metadata_extractor: MetadataAgent,
        risk_analyzer: RiskAgent,
        graph_extractor: GraphAgent,
        storage_evaluator: StorageAgent
    ) -> None:
        """Initializes the workflow with initialized agent instances."""
        self.classifier = classifier
        self.metadata_extractor = metadata_extractor
        self.risk_analyzer = risk_analyzer
        self.graph_extractor = graph_extractor
        self.storage_evaluator = storage_evaluator
        logger.debug("IngestionWorkflow orchestrator initialized.")

    def process_chunk(self, text: str) -> DocumentProcessingState:
        """Runs the text through the full suite of analysis agents.

        This pipeline processes the agents sequentially. In a high-throughput 
        production environment, several of these steps (like risk, graph, and 
        metadata) could be executed asynchronously in parallel.

        Args:
            text: The raw document text chunk to process.

        Returns:
            A DocumentProcessingState containing the combined agent outputs.
        """
        state = DocumentProcessingState(chunk_text=text)

        if not text or len(text.strip()) < 10:
            logger.warning("Workflow received empty or very short text. Skipping processing.")
            return state

        logger.info(f"Starting agent workflow for text chunk (Length: {len(text)})")

        # Step 1: Storage & Routing Evaluation
        # We do this first so we can abort early if the text is garbage.
        logger.debug("Executing Storage Agent...")
        state.storage_decision = self.storage_evaluator.evaluate_for_storage(text)
        
        if not state.storage_decision.should_store:
            logger.info("Storage Agent rejected chunk. Aborting workflow.")
            return state

        # Step 2: Classification
        logger.debug("Executing Classifier Agent...")
        try:
            state.classification = self.classifier.classify_text(text)
        except Exception as e:
            logger.error(f"Workflow classification step failed: {e}")

        # Step 3: Metadata Extraction
        logger.debug("Executing Metadata Agent...")
        state.metadata = self.metadata_extractor.extract_metadata(text)

        # Step 4: Risk Analysis
        logger.debug("Executing Risk Agent...")
        state.risks = self.risk_analyzer.analyze_risks(text)

        # Step 5: Graph Extraction
        logger.debug("Executing Graph Agent...")
        state.graph_data = self.graph_extractor.extract_graph_data(text)

        logger.info("Agent workflow completed successfully.")
        return state

    def format_for_storage(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Converts the processed state into a flat dictionary for the vector DB."""
        if not state.storage_decision or not state.storage_decision.should_store:
            return {}

        payload: Dict[str, Any] = {
            "page_content": state.chunk_text,
            "metadata": {
                "collection": state.storage_decision.primary_collection,
                "routing_tags": state.storage_decision.tags
            }
        }

        if state.classification:
            payload["metadata"]["category"] = state.classification.category.value
            
        if state.metadata:
            payload["metadata"]["title"] = state.metadata.title
            payload["metadata"]["author"] = state.metadata.author
            payload["metadata"]["keywords"] = state.metadata.keywords

        if state.risks:
            payload["metadata"]["risk_level"] = state.risks.overall_risk_level
            payload["metadata"]["risk_count"] = len(state.risks.identified_risks)

        return payload