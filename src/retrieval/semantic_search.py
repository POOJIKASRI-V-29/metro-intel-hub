import logging
from typing import List, Dict, Any
from src.embeddings.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

class SemanticSearch:
    def __init__(self):
        self.vector_store = ChromaVectorStore()

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieves relevant chunks from the vector store."""
        logger.info(f"Retrieving documents for query: {query}")
        return self.vector_store.search(query, top_k=top_k)