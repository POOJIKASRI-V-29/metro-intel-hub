"""
Document Retrieval and Semantic Search Pipeline for the KMRL Platform.

This module orchestrates the extraction of relevant document context by embedding
user queries and executing highly optimized approximate nearest neighbor (ANN) 
searches against the vector database.
"""

import logging
from typing import Any, Dict, List, Optional

# Import orchestrators and schemas from previous stages
from ..embeddings.manager import EmbeddingManager
from ..vector_store.base import BaseVectorStore, SearchFilter, SearchResult

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.retrieval_pipeline")


class RetrievalPipeline:
    """
    Master pipeline orchestrating user queries into semantic document retrievals.
    """

    def __init__(
        self,
        embedder: EmbeddingManager,
        vector_store: BaseVectorStore,
        target_collection: str = "kmrl_enterprise_docs"
    ) -> None:
        """
        Initializes the retrieval pipeline with required engine dependencies.

        Args:
            embedder: Configured EmbeddingManager instance for vectorizing queries.
            vector_store: Active Vector DB connection instance.
            target_collection: The database collection name to query against.
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.target_collection = target_collection

    def retrieve_context(
        self, 
        query: str, 
        top_k: int = 5, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Executes an end-to-end semantic search based on a raw text query.

        Args:
            query: The natural language question or search string provided by the user.
            top_k: The maximum number of relevant context chunks to return.
            filters: Optional dictionary of key-value pairs to restrict the search space 
                     (e.g., {"document_id": "123", "department": "engineering"}).

        Returns:
            A prioritized, ordered list of SearchResult objects containing text and similarity scores.
        """
        if not query or not query.strip():
            logger.warning("Empty search query received. Aborting retrieval pipeline.")
            return []

        logger.info(f"--- Starting retrieval pipeline for query: '{query}' ---")

        try:
            # Step 1: Format dynamic dictionary filters into strict structural schemas
            search_filters: List[SearchFilter] = []
            if filters:
                for key, value in filters.items():
                    search_filters.append(SearchFilter(key=key, value=value))
                logger.debug(f"Applied {len(search_filters)} metadata constraints to the query parameters.")

            # Step 2: Convert the text query into a dense numerical vector
            logger.debug("Generating dense vector embedding for query text...")
            query_vector = self.embedder.generate_single_query_embedding(query)

            # Step 3: Execute the similarity search against the vector database
            logger.debug(f"Executing database similarity search on collection '{self.target_collection}'...")
            results = self.vector_store.search_similarity(
                collection_name=self.target_collection,
                query_vector=query_vector,
                top_k=top_k,
                filters=search_filters if search_filters else None
            )

            logger.info(f"--- Retrieval completed. Found {len(results)} matching contexts. ---")
            return results

        except Exception as error:
            logger.exception("The retrieval pipeline encountered a fatal execution failure.")
            raise RuntimeError(f"Failed to retrieve context for query: {str(error)}") from error