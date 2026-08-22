"""
Human-Facing Semantic Search Pipeline for the KMRL Platform.

This module orchestrates document-level search queries. It wraps the raw chunk 
retrieval engine and applies grouping, document-level scoring, and snippet 
extraction to render UI-ready search results.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import the core retrieval engine
from .retrieval_pipeline import RetrievalPipeline

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.search_pipeline")


class SearchSnippet(BaseModel):
    """
    A specific textual match inside a broader document.
    """
    chunk_id: str = Field(..., description="Unique identifier of the exact text chunk.")
    text: str = Field(..., description="The raw textual snippet to display to the user.")
    score: float = Field(..., description="The localized vector similarity score.")


class DocumentSearchResult(BaseModel):
    """
    A grouped, document-level search result ready for UI presentation.
    """
    document_id: str = Field(..., description="The unique ID of the parent document.")
    filename: str = Field(..., description="The original uploaded filename.")
    relevance_score: float = Field(..., description="The aggregated document-level matching score.")
    snippets: List[SearchSnippet] = Field(..., description="List of highly relevant contextual matches within this document.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document-level tags (e.g., author, upload_date).")


class SearchPipeline:
    """
    Orchestrates UI-focused document search, applying post-retrieval grouping and aggregation.
    """

    def __init__(self, retrieval_pipeline: RetrievalPipeline) -> None:
        """
        Initializes the search pipeline.

        Args:
            retrieval_pipeline: Configured instance of the raw vector retrieval pipeline.
        """
        self.retrieval_pipeline = retrieval_pipeline

    def execute_search(
        self, 
        query: str, 
        top_k_chunks: int = 20, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DocumentSearchResult]:
        """
        Executes a semantic search and aggregates the hits into unified document profiles.

        Args:
            query: The user's search string.
            top_k_chunks: The depth of chunks to fetch before grouping. A higher number 
                          provides better document aggregation at the cost of slight latency.
            filters: Optional dictionary of metadata constraints.

        Returns:
            An ordered list of DocumentSearchResult objects, ranked by relevance.
        """
        logger.info(f"--- Executing document search for query: '{query}' ---")

        try:
            # Step 1: Fetch raw chunk hits from the underlying retrieval engine
            raw_chunks = self.retrieval_pipeline.retrieve_context(
                query=query, 
                top_k=top_k_chunks, 
                filters=filters
            )

            if not raw_chunks:
                logger.info("No matching documents found.")
                return []

            # Step 2: Group the isolated chunks by their parent document ID
            grouped_docs: Dict[str, dict] = defaultdict(lambda: {
                "snippets": [],
                "filename": "Unknown Document",
                "metadata": {}
            })

            for chunk in raw_chunks:
                doc_id = chunk.metadata.get("document_id", "unknown_doc_id")
                
                # Capture document-level metadata from the highest-scoring chunk of that document
                if not grouped_docs[doc_id]["snippets"]:
                    grouped_docs[doc_id]["filename"] = chunk.metadata.get("filename", doc_id)
                    # Extract pure document metadata, omitting chunk-specific operational tags
                    clean_meta = {k: v for k, v in chunk.metadata.items() if k not in ["document_id", "filename", "chunk_index"]}
                    grouped_docs[doc_id]["metadata"] = clean_meta

                grouped_docs[doc_id]["snippets"].append(
                    SearchSnippet(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        score=chunk.score
                    )
                )

            # Step 3: Calculate document-level scores and compile the final schemas
            final_results: List[DocumentSearchResult] = []
            
            for doc_id, data in grouped_docs.items():
                snippets = data["snippets"]
                
                # The document relevance score is determined by its single highest-matching snippet
                # (Alternatively, you could average the top 3 snippet scores for a density metric)
                max_score = max(s.score for s in snippets)

                final_results.append(
                    DocumentSearchResult(
                        document_id=doc_id,
                        filename=data["filename"],
                        relevance_score=max_score,
                        snippets=snippets,
                        metadata=data["metadata"]
                    )
                )

            # Step 4: Sort the aggregated documents by their global relevance score (descending)
            final_results.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.info(f"Search successfully grouped into {len(final_results)} distinct documents.")
            return final_results

        except Exception as error:
            logger.exception("The search pipeline encountered an error during execution.")
            raise RuntimeError(f"Failed to execute document search: {str(error)}") from error