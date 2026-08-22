"""Content recommendation analysis service.

Scope: Analyzes document metadata, tags, and user queries to suggest 
related content within the KMRL platform. This service bridges the gap 
between static search and proactive knowledge discovery.
"""

from __future__ import annotations

from typing import List, Dict, Any

from config.logging import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """Service to generate content recommendations based on context."""

    def __init__(self, vector_retriever: Any = None) -> None:
        """Initializes the recommendation engine.

        Args:
            vector_retriever: A dependency-injected client or function 
                capable of performing similarity searches in the vector database.
        """
        self.retriever = vector_retriever
        logger.debug("RecommendationService initialized.")

    def get_related_documents(self, keywords: List[str], current_doc_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Finds related documents based on shared keywords or vector similarity.

        Args:
            keywords: A list of keywords extracted from the current document.
            current_doc_id: The ID of the document currently being viewed 
                (used to exclude it from the results).
            limit: The maximum number of recommendations to return.

        Returns:
            A list of dictionaries containing metadata of recommended documents.
        """
        if not keywords:
            logger.info("No keywords provided for recommendation. Returning empty list.")
            return []

        if not self.retriever:
            logger.warning("No vector retriever configured. Cannot fetch real recommendations.")
            # Fallback for when the DB is not wired up yet
            return [{"id": "mock_id_1", "title": "Mock Related Document", "match_reason": "Fallback"}]

        logger.debug(f"Fetching recommendations based on keywords: {keywords}")
        
        try:
            # Create a synthetic query from the keywords to search the vector DB
            search_query = " ".join(keywords)
            
            # Assuming the retriever has a semantic_search method returning raw chunks/docs
            raw_results = self.retriever.semantic_search(search_query, top_k=limit + 1)
            
            recommendations = []
            for res in raw_results:
                # Exclude the current document from recommendations
                doc_id = res.get("metadata", {}).get("document_id")
                if doc_id == current_doc_id:
                    continue
                    
                recommendations.append({
                    "document_id": doc_id,
                    "title": res.get("metadata", {}).get("title", "Untitled Document"),
                    "category": res.get("metadata", {}).get("category", "Unknown"),
                    "similarity_score": res.get("score", 0.0)
                })
                
                if len(recommendations) >= limit:
                    break
                    
            return recommendations

        except Exception as exc:
            logger.error(f"Failed to fetch related documents: {exc}")
            return []

    def get_trending_categories(self, recent_queries: List[str]) -> List[str]:
        """Analyzes recent user queries to recommend trending topic categories.

        Args:
            recent_queries: A list of recent search strings from users.

        Returns:
            A curated list of trending category names.
        """
        # In a full implementation, this would map queries to categories 
        # using an LLM or predefined taxonomy, then count frequencies.
        # For now, we return a static fallback or basic logic.
        logger.debug(f"Analyzing {len(recent_queries)} recent queries for trends.")
        return ["Safety Protocols", "Maintenance Logs", "Standard Operating Procedures"]