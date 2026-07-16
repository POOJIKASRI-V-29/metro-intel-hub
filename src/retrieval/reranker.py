"""Second-stage document reranker for the KMRL platform.

Scope: Improves RAG search accuracy by scoring and reordering the initial 
vector search results using a highly accurate cross-encoder model.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Note: Requires `pip install sentence-transformers`
from sentence_transformers import CrossEncoder

from config.logging import get_logger
from utils.loggers import log_execution_time

logger = get_logger(__name__)


class DocumentReranker:
    """Evaluates and reorders search results for maximum context relevance."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        """Initializes the cross-encoder reranking model.

        Args:
            model_name: The Hugging Face registry string for the reranker model.
        """
        logger.info(f"Loading DocumentReranker model: {model_name}")
        try:
            # CrossEncoders process the query and document simultaneously for higher accuracy
            self.model = CrossEncoder(model_name, max_length=512)
        except Exception as e:
            logger.critical(f"Failed to load reranker model: {str(e)}")
            raise RuntimeError(f"Reranker boot failure: {str(e)}") from e

    @log_execution_time
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Scores and reorders a list of candidate documents against the query.

        Args:
            query: The exact search question asked by the user.
            documents: The initial list of document chunks returned by the vector DB.
                Expected format: [{"text": "...", "metadata": {...}}, ...]
            top_k: The final number of top-scoring documents to return.

        Returns:
            A sorted list of the top `top_k` documents, annotated with new relevance scores.
        """
        if not documents:
            logger.warning("No documents provided to the reranker. Skipping.")
            return []

        logger.debug(f"Reranking {len(documents)} candidate documents for query: '{query[:30]}...'")

        # Format inputs for the CrossEncoder: a list of (query, document_text) pairs
        sentence_pairs = [[query, doc["text"]] for doc in documents]

        try:
            # The model returns a list of float scores corresponding to each pair
            scores = self.model.predict(sentence_pairs)
        except Exception as e:
            logger.error(f"Error during cross-encoder prediction: {str(e)}")
            raise e

        # Attach the new scores to the original document dictionaries
        for idx, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[idx])

        # Sort the documents descending based on their new, highly accurate score
        sorted_documents = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # Trim the list to the requested top_k limit
        final_results = sorted_documents[:top_k]
        
        logger.info(f"Reranking complete. Top score: {final_results[0]['rerank_score']:.4f}")
        return final_results